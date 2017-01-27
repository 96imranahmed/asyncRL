import numpy as np
import tensorflow as tf

NUM_GOALS = 20
NUM_CUBES = 4
MAIN_OUTPUT_SIZE = 200

def build_main_network(state, add_summaries=False):

  # Five FC layers
  fc_1 = tf.contrib.layers.fully_connected(state, 400, activation_fn=tf.nn.relu)
  fc_2 = tf.contrib.layers.fully_connected(fc_1, 400, activation_fn=tf.nn.relu)
  fc_3 = tf.contrib.layers.fully_connected(fc_2, 300, activation_fn=tf.nn.relu)
  fc_4 = tf.contrib.layers.fully_connected(fc_3, 300, activation_fn=tf.nn.relu)
  fc_5 = tf.contrib.layers.fully_connected(fc_4, 300, activation_fn=tf.nn.relu)
  fc_6 = tf.contrib.layers.fully_connected(fc_5, 200, activation_fn=tf.nn.relu)
  fc_7 = tf.contrib.layers.fully_connected(fc_6, MAIN_OUTPUT_SIZE, activation_fn=tf.nn.relu)

  if add_summaries:
    tf.contrib.layers.summarize_activation(fc_1)
    tf.contrib.layers.summarize_activation(fc_2)
    tf.contrib.layers.summarize_activation(fc_3)
    tf.contrib.layers.summarize_activation(fc_4)
    tf.contrib.layers.summarize_activation(fc_5)
    tf.contrib.layers.summarize_activation(fc_6)
    tf.contrib.layers.summarize_activation(fc_7)

  return fc_7


class DuelingDDQN():

  def __init__(self, reuse=False, trainable=True):
    self.num_actions = 4
    self.state_vec_size = 4*NUM_CUBES + 2*NUM_GOALS + 1 # TODO actually fix this
    # Placeholders for our input
    self.states = tf.placeholder(shape=[None, self.state_vec_size], dtype=tf.float32, name="states")
    # The TD target value
    self.target_q = tf.placeholder(shape=[None], dtype=tf.float32, name="target_q")
    #self.actions = tf.placeholder(shape=[None],dtype=tf.int32)

    # TODO - fix this for windows - pull windows branch and then see
    # updated - fixed for windows
    self.actions_onehot = tf.placeholder(shape=[None,self.num_actions],dtype=tf.float32)


    # Build base part of net and get output
    self.op_shared = build_main_network(self.states, add_summaries=(not reuse))

    # separate op_shared into advantage and value streams
    # TODO check this is actually doing what it should be
    self.stream_a,self.stream_v = tf.split(1,2,self.op_shared)

    # TODO - 200 (op shared size) is hardcoded, probably better to define somewhere
    self.advantage_weights = tf.Variable(tf.random_normal([int(MAIN_OUTPUT_SIZE/2),self.num_actions]))
    self.value_weights = tf.Variable(tf.random_normal([int(MAIN_OUTPUT_SIZE/2),1]))

    self.advantage = tf.matmul(self.stream_a,self.advantage_weights)
    self.value = tf.matmul(self.stream_v, self.value_weights)

    #Combine above two together to get q out and the predictions
    self.q_out = self.value + tf.sub(self.advantage,tf.reduce_mean(self.advantage,reduction_indices=1,keep_dims=True))
    self.predict = tf.argmax(self.q_out,1)

    # now calculate the selected q values
    self.selected_q = tf.reduce_sum(tf.mul(self.q_out, self.actions_onehot), reduction_indices=1)
    self.error = tf.square(self.target_q - self.selected_q)
    self.loss = tf.reduce_mean(self.error, name="loss")

    # this below is to help us deal with the global shared network also
    if trainable:
      self.optimizer = tf.train.AdamOptimizer(1e-4)
      #self.optimizer = tf.train.RMSPropOptimizer(0.00025, 0.99, 0.0, 1e-6)
      self.grads_and_vars = self.optimizer.compute_gradients(self.loss)
      self.grads_and_vars = [[grad, var] for grad, var in self.grads_and_vars if grad is not None]
      self.train_op = self.optimizer.apply_gradients(self.grads_and_vars,
        global_step=tf.contrib.framework.get_global_step())

    # # Summaries
    # prefix = tf.get_variable_scope().name
    # tf.scalar_summary(self.loss.name, self.loss)
    # tf.scalar_summary("{}/max_value".format(prefix), tf.reduce_max(self.logits))
    # tf.scalar_summary("{}/min_value".format(prefix), tf.reduce_min(self.logits))
    # tf.scalar_summary("{}/mean_value".format(prefix), tf.reduce_mean(self.logits))
    # tf.scalar_summary("{}/reward_max".format(prefix), tf.reduce_max(self.targets))
    # tf.scalar_summary("{}/reward_min".format(prefix), tf.reduce_min(self.targets))
    # tf.scalar_summary("{}/reward_mean".format(prefix), tf.reduce_mean(self.targets))
    # tf.histogram_summary("{}/reward_targets".format(prefix), self.targets)
    # tf.histogram_summary("{}/values".format(prefix), self.logits)
    # var_scope_name = tf.get_variable_scope().name
    # summary_ops = tf.get_collection(tf.GraphKeys.SUMMARIES)
    # sumaries = [s for s in summary_ops if "policy_net" in s.name or "shared" in s.name]
    # sumaries = [s for s in summary_ops if var_scope_name in s.name]
    # self.summaries = tf.merge_summary(sumaries)