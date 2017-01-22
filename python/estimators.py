import numpy as np
import tensorflow as tf

def build_shared_network(state, add_summaries=False):
  """
  Builds a 3-layer network
  Args:
    state: Inputs
    add_summaries: If true, add layer summaries to Tensorboard.
  Returns:
    Final layer activations.
  """

  # Three convolutional layers
  fc_1 = tf.contrib.layers.fully_connected(state, 100, activation_fn=tf.nn.relu)
  fc_2 = tf.contrib.layers.fully_connected(fc_1, 100, activation_fn=tf.nn.relu)
  fc_3 = tf.contrib.layers.fully_connected(fc_2, 50, activation_fn=tf.nn.relu)

  if add_summaries:
    tf.contrib.layers.summarize_activation(fc_1)
    tf.contrib.layers.summarize_activation(fc_2)
    tf.contrib.layers.summarize_activation(fc_3)

  return fc_3

class PolicyEstimator():
  """
  Policy Function approximator. Given a observation, returns probabilities
  over all possible actions.
  Args:
    num_outputs: Size of the action space.
    reuse: If true, an existing shared network will be re-used.
    trainable: If true we add train ops to the network.
      Actor threads that don't update their local models and don't need
      train ops would set this to false.
  """

  def __init__(self, num_outputs, reuse=False, trainable=True):
    self.num_outputs = num_outputs
    self.state_vec_size = 30 # TODO actually fix this

    # Placeholders for our input
    self.states = tf.placeholder(shape=[None, self.state_vec_size], dtype=tf.float32, name="states")
    # The TD target value - generated from the other network (value network)
    self.targets = tf.placeholder(shape=[None], dtype=tf.float32, name="y")
    # Integer id of which action was selected
    self.actions = tf.placeholder(shape=[None], dtype=tf.int32, name="actions")

    # Normalize
    X = tf.to_float(self.states)
    batch_size = tf.shape(self.states)[0]

    # Graph shared with Value Net
    with tf.variable_scope("shared", reuse=reuse):
      op_shared = build_shared_network(X, add_summaries=(not reuse))


    with tf.variable_scope("policy_net"):
      self.logits = tf.contrib.layers.fully_connected(op_shared, num_outputs, activation_fn=None)
      self.probs = tf.nn.softmax(self.logits) + 1e-8

      self.predictions = {
        "logits": self.logits,
        "probs": self.probs
      }

      # We add entropy to the loss to encourage exploration
      self.entropy = -tf.reduce_sum(self.probs * tf.log(self.probs), 1, name="entropy")
      self.entropy_mean = tf.reduce_mean(self.entropy, name="entropy_mean")

      # Get the predictions for the chosen actions only
      gather_indices = tf.range(batch_size) * tf.shape(self.probs)[1] + self.actions
      self.picked_action_probs = tf.gather(tf.reshape(self.probs, [-1]), gather_indices)

      self.losses = - (tf.log(self.picked_action_probs) * self.targets + 0.01 * self.entropy)
      self.loss = tf.reduce_sum(self.losses, name="loss")

      tf.scalar_summary(self.loss.op.name, self.loss)
      tf.scalar_summary(self.entropy_mean.op.name, self.entropy_mean)
      tf.histogram_summary(self.entropy.op.name, self.entropy)

      if trainable:
        self.optimizer = tf.train.AdamOptimizer(1e-4)
        #self.optimizer = tf.train.RMSPropOptimizer(0.00025, 0.99, 0.0, 1e-6)
        self.grads_and_vars = self.optimizer.compute_gradients(self.loss)
        self.grads_and_vars = [[grad, var] for grad, var in self.grads_and_vars if grad is not None]
        self.train_op = self.optimizer.apply_gradients(self.grads_and_vars,
          global_step=tf.contrib.framework.get_global_step())

    # Merge summaries from this network and the shared network (but not the value net)
    var_scope_name = tf.get_variable_scope().name
    summary_ops = tf.get_collection(tf.GraphKeys.SUMMARIES)
    summaries = [s for s in summary_ops if "policy_net" in s.name or "shared" in s.name]
    summaries = [s for s in summary_ops if var_scope_name in s.name]
    self.summaries = tf.merge_summary(summaries)


class ValueEstimator():
  """
  Value Function approximator. Returns a value estimator for a batch of observations.
  Args:
    reuse: If true, an existing shared network will be re-used.
    trainable: If true we add train ops to the network.
      Actor threads that don't update their local models and don't need
      train ops would set this to false.
  """

  def __init__(self, reuse=False, trainable=True):
     self.state_vec_size = 30 # TODO actually fix this
    # Placeholders for our input
    self.states = tf.placeholder(shape=[None, self.state_vec_size], dtype=tf.float32, name="states")
    # The TD target value
    self.targets = tf.placeholder(shape=[None], dtype=tf.float32, name="y")

    X = tf.to_float(self.states)

    # Graph shared with Value Net
    with tf.variable_scope("shared", reuse=reuse):
      op_shared = build_shared_network(X, add_summaries=(not reuse))

    with tf.variable_scope("value_net"):
      self.logits = tf.contrib.layers.fully_connected(
        inputs=op_shared,
        num_outputs=1,
        activation_fn=None)
      self.logits = tf.squeeze(self.logits, squeeze_dims=[1], name="logits")

      self.losses = tf.squared_difference(self.logits, self.targets)
      self.loss = tf.reduce_sum(self.losses, name="loss")

      self.predictions = {
        "logits": self.logits
      }

      # Summaries
      prefix = tf.get_variable_scope().name
      tf.scalar_summary(self.loss.name, self.loss)
      tf.scalar_summary("{}/max_value".format(prefix), tf.reduce_max(self.logits))
      tf.scalar_summary("{}/min_value".format(prefix), tf.reduce_min(self.logits))
      tf.scalar_summary("{}/mean_value".format(prefix), tf.reduce_mean(self.logits))
      tf.scalar_summary("{}/reward_max".format(prefix), tf.reduce_max(self.targets))
      tf.scalar_summary("{}/reward_min".format(prefix), tf.reduce_min(self.targets))
      tf.scalar_summary("{}/reward_mean".format(prefix), tf.reduce_mean(self.targets))
      tf.histogram_summary("{}/reward_targets".format(prefix), self.targets)
      tf.histogram_summary("{}/values".format(prefix), self.logits)

      if trainable:
        self.optimizer = tf.train.AdamOptimizer(1e-4)
        #self.optimizer = tf.train.RMSPropOptimizer(0.00025, 0.99, 0.0, 1e-6)
        self.grads_and_vars = self.optimizer.compute_gradients(self.loss)
        self.grads_and_vars = [[grad, var] for grad, var in self.grads_and_vars if grad is not None]
        self.train_op = self.optimizer.apply_gradients(self.grads_and_vars,
          global_step=tf.contrib.framework.get_global_step())

    var_scope_name = tf.get_variable_scope().name
    summary_ops = tf.get_collection(tf.GraphKeys.SUMMARIES)
    sumaries = [s for s in summary_ops if "policy_net" in s.name or "shared" in s.name]
    sumaries = [s for s in summary_ops if var_scope_name in s.name]
    self.summaries = tf.merge_summary(sumaries)