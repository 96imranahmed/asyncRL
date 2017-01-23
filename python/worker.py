import sys
import os
import itertools
import collections
import numpy as np
import tensorflow as tf
import connect

from inspect import getsourcefile
current_path = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
import_path = os.path.abspath(os.path.join(current_path, "../.."))

if import_path not in sys.path:
  sys.path.append(import_path)

from estimators import DuelingDDQN

# Transition = collections.namedtuple("Transition", ["state", "action", "reward", "next_state", "done"])


# buffer should be a list of transition tuples
# when we call experience_buffer.add(exp) need to make sure exp is a list of transition tuples also
class experience_buffer():
  def __init__(self, buffer_size = 50000):
    self.buffer = []
    self.buffer_size = buffer_size
  
  def add(self,experience):
    if len(self.buffer) + len(experience) >= self.buffer_size:
        self.buffer[0:(len(experience)+len(self.buffer))-self.buffer_size] = []
    self.buffer.extend(experience)
        
  def sample(self,size):
    return np.reshape(np.array(random.sample(self.buffer,size)),[size,5])



def make_copy_params_op(v1_list, v2_list, tau=None):
  """
  Creates an operation that copies parameters from variable in v1_list to variables in v2_list.
  The ordering of the variables in the lists must be identical.
  """
  v1_list = list(sorted(v1_list, key=lambda v: v.name))
  v2_list = list(sorted(v2_list, key=lambda v: v.name))

  update_ops = []

  for v1, v2 in zip(v1_list, v2_list):
    if tau is None:
      op = v2.assign(v1)
    else:
      op = v2.assign((v1.value()*tau) + ((1-tau)*v1.value()))
    update_ops.append(op)
  return update_ops


def make_train_op(local_estimator, global_estimator):
  """
  Creates an op that applies local estimator gradients
  to the global estimator.
  """
  local_grads, _ = zip(*local_estimator.grads_and_vars)
  # Clip gradients
  local_grads, _ = tf.clip_by_global_norm(local_grads, 5.0)
  _, global_vars = zip(*global_estimator.grads_and_vars)
  local_global_grads_and_vars = list(zip(local_grads, global_vars))
  return global_estimator.optimizer.apply_gradients(local_global_grads_and_vars,
          global_step=tf.contrib.framework.get_global_step())


class Worker(object):
  def __init__(self, lock_in, id_in, name, global_net, global_counter, discount_factor=0.99, summary_writer=None, max_global_steps=None):
    self.name = name
    self.lock = lock_in
    self.id = id_in
    self.discount_factor = discount_factor
    self.max_global_steps = max_global_steps
    self.global_step = tf.contrib.framework.get_global_step()
    self.global_network = global_net
    self.global_counter = global_counter
    self.local_counter = itertools.count()
    #self.sp = StateProcessor() # NEEDS FIXING
    self.summary_writer = summary_writer
    #self.env = env #need to set this up with a private simulation environment
    self.replay_memory = experience_buffer() # needed to allow for exeperience replay
    self.batch_size = 32 # how many items to sample from the experience when training

    self.start_epsilon = 1
    self.end_epsilon = 0.1
    self.annealing_steps = 30000
    self.epsilon = self.start_epsilon

    self.done = False
    self.net_reward = 0

    self.epsilon_update = float(self.start_epsilon-self.end_epsilon)/float(self.annealing_steps)

    #Websocket stuff
    self.ws = connect.create_socket('sclient:'+str(self.id))

    # Create two local q nets - target and main
    with tf.variable_scope(name + "main"):
      self.main_qn = DuelingDDQN()
    with tf.variable_scope(name + "target"):
      self.target_qn = DuelingDDQN()

    # Op to copy params from global policy/valuenets
    self.copy_params_op = make_copy_params_op(
      tf.contrib.slim.get_variables(scope="global", collection=tf.GraphKeys.TRAINABLE_VARIABLES),
      tf.contrib.slim.get_variables(scope=(self.name + "main"), collection=tf.GraphKeys.TRAINABLE_VARIABLES))

    #Need an operation here to copy params (at rate tau) from main network to target network
    self.copy_params_to_target = make_copy_params_op(
      tf.contrib.slim.get_variables(scope=(self.name + "main"), collection=tf.GraphKeys.TRAINABLE_VARIABLES), 
      tf.contrib.slim.get_variables(scope=(self.name + "target"), collection=tf.GraphKeys.TRAINABLE_VARIABLES),
      tau = 0.001)

    self.global_train_op = make_train_op(self.main_qn, self.global_network)

    self.state = None


  def run(self, sess, coord, t_max):
    with sess.as_default(), sess.graph.as_default():
      # Initial state
      self.state = connect.state(connect.send_message_sync(self.ws, 'c'+str(self.id)+':-1', str(self.id), self.lock)) #Sends reset flag to simulation on behalf of current client
      #self.state = atari_helpers.atari_make_initial_state(self.sp.process(self.env.reset())) # Needs fixing - need to make initial state using Imran's reset code
      try:
        # first of all, logic here to store some stuff in the experience replay
        INITIAL_STEPS = 2000
        self.build_replay_memory(INITIAL_STEPS, sess)

        EPISODE_LENGTH = 1500
        total_steps_done = 0
        while not coord.should_stop():
          # while not stop:
          # run one step, store in replay memory
          # if step number %4 == 0 , call copy params op and copy target op
          # sample to get past transitions
          # call update on this
          self.state = connect.state(connect.send_message_sync(self.ws, 'c'+str(self.id)+':-1', str(self.id),  self.lock))
          timestep = 0
          self.net_reward = 0 # total episode reward - reset to zero at the end of every episode

          while timestep < EPISODE_LENGTH:

            timestep += 1
            total_steps_done += 1
            
            if epsilon > self.end_epsilon:
              epsilon -= self.epsilon_update

            self.run_one_step(sess)

            if timestep % 4 == 0:
              # sample from experience
              train_batch = self.replay_memory.sample(self.batch_size)

              self.update(train_batch,sess)

              sess.run(self.copy_params_op)
              sess.run(self.copy_params_to_target)

      except tf.errors.CancelledError:
        return


  # take a step from self.state with epsilon greedy policy
  # store transition in replay memory
  # update self.net_reward and state information
  def run_one_step(self, sess):
    #Choose an action by greedily (with e chance of random action) from the Q-network
    if np.random.rand(1) < self.epsilon:
      action = np.random.randint(0,4)
      print("choosing random action, it is ", action)
    else:
      action = sess.run(self.main_qn.predict,feed_dict={main_qn.states:[self.state]})[0]
      print("choosing action from network output, it is ", action)

    next_state, reward, done = connect.state(connect.send_message_sync(self.ws, 'c'+str(self.id)+':'+str(action), str(self.id), self.lock)) # TODO implement this client side
   
    self.replay_memory.add(np.reshape(np.array([self.state,action,reward,next_state,done]),[1,5]))

    # Increase local and global counters
    local_t = next(self.local_counter)
    global_t = next(self.global_counter)

    if local_t % 100 == 0:
      tf.logging.info("{}: local Step {}, global step {}".format(self.name, local_t, global_t))

    self.state = next_state
    self.net_reward += reward


  # this is probably ok as is, just adding to replay memory
  def build_replay_memory(self, steps, sess):
    for _ in range(steps):
      # Take a step, completely at random, and tick over the simulation
      action = np.random.randint(0,4)
      next_state, reward, done, _ = connect.state(connect.send_message_sync(self.ws, 'c'+str(self.id)+':'+str(action), str(self.id),  self.lock))

      # Store transition
      self.replay_memory.add(np.reshape(np.array([self.state,action,reward,next_state,done]),[1,5]))
      self.state = next_state




  # TODO - this needs changing - can get rid of a lot of the complexity with regards to calculating rewards
  # TODO - should mirror part of the simple_sim. Structure here is a lot better, so use this
  def update(self, train_batch, sess):

    actions_from_q1 = sess.run(main_qn.predict,feed_dict={main_qn.states:np.vstack(train_batch[:,3])})

    all_q_vals = sess.run(target_qn.q_out,feed_dict={target_qn.states:np.vstack(trainBatch[:,3])})

    end_multiplier = -(train_batch[:,4] - 1)

    double_q_values = all_q_vals[range(batch_size),actions_from_q1]
    target_q_vals = train_batch[:,2] + (self.discount_factor * double_q_values * end_multiplier)

    feeder = {
      self.main_qn.states: np.vstack(train_batch[:,0]),
      self.main_qn.target_q: target_q_vals,
      self.main_qn.actions: train_batch[:,1]
    }

    global_step, main_qn_loss, _,_ = sess.run([
      self.global_step,
      self.main_qn.loss,
      self.main_qn.train_op,
      self.global_train_op]
      , feed_dict=feeder)

    # todo add summaries also

    # # Write summaries
    # if self.summary_writer is not None:
    #   self.summary_writer.add_summary(pnet_summaries, global_step)
    #   self.summary_writer.add_summary(vnet_summaries, global_step)
    #   self.summary_writer.flush()

    # return pnet_loss, vnet_loss, pnet_summaries, vnet_summaries