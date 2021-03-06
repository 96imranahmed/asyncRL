#! /usr/bin/env python

import unittest
#import gym
import sys
import os
import numpy as np
import tensorflow as tf
import itertools
import shutil
import threading
import multiprocessing

from inspect import getsourcefile
current_path = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
import_path = os.path.abspath(os.path.join(current_path, "../.."))

if import_path not in sys.path:
  sys.path.append(import_path)

#from lib.atari import helpers as atari_helpers
from estimators import DuelingDDQN
#from policy_monitor import PolicyMonitor
from worker import Worker


tf.flags.DEFINE_string("model_dir", "./tmp/a3c", "Directory to write Tensorboard summaries and videos to.")
#tf.flags.DEFINE_string("env", "Breakout-v0", "Name of gym Atari environment, e.g. Breakout-v0")
tf.flags.DEFINE_integer("t_max", 5, "Number of steps before performing an update")
tf.flags.DEFINE_integer("max_global_steps", None, "Stop training after this many steps in the environment. Defaults to running indefinitely.")
tf.flags.DEFINE_integer("eval_every", 300, "Evaluate the policy every N seconds")
tf.flags.DEFINE_boolean("reset", False, "If set, delete the existing model directory and start training from scratch.")
tf.flags.DEFINE_integer("parallelism", None, "Number of threads to run. If not set we run [num_cpu_cores] threads.")

FLAGS = tf.flags.FLAGS

VALID_ACTIONS = list(range(4))

# Set the number of workers
NUM_WORKERS = 4
if FLAGS.parallelism:
  NUM_WORKERS = FLAGS.parallelism

MODEL_DIR = FLAGS.model_dir
CHECKPOINT_DIR = os.path.join(MODEL_DIR, "checkpoints")

# Optionally empty model directory
if FLAGS.reset:
  shutil.rmtree(MODEL_DIR, ignore_errors=True)

if not os.path.exists(CHECKPOINT_DIR):
  os.makedirs(CHECKPOINT_DIR)

summary_writer = tf.summary.FileWriter(os.path.join(MODEL_DIR, "train"))

with tf.device("/cpu:0"):

  # Keeps track of the number of updates we've performed
  global_step = tf.Variable(0, name="global_step", trainable=False)

  with tf.variable_scope("global") as vs:
    global_network = DuelingDDQN()

  # Global step iterator
  global_counter = itertools.count()

  # Create worker graphs
  workers = []
  for worker_id in range(NUM_WORKERS):
    # We only write summaries in one of the workers because they're
    # pretty much identical and writing them on all workers
    # would be a waste of space
    worker_summary_writer = None
    if worker_id == 0:
      worker_summary_writer = summary_writer

    # we have to augment this to include some information about the environment
    lady_lock = threading.Lock()
    worker = Worker(
      lock_in = lady_lock,  
      id_in = worker_id,
      name ="worker_{}".format(worker_id),
      global_net=global_network,
      global_counter=global_counter,
      discount_factor = 0.99,
      summary_writer=worker_summary_writer,
      max_global_steps=FLAGS.max_global_steps)
    workers.append(worker)

with tf.Session() as sess:
  sess.run(tf.initialize_all_variables())
  coord = tf.train.Coordinator()

  # Load a previous checkpoint if it exists
  latest_checkpoint = tf.train.latest_checkpoint(CHECKPOINT_DIR)
  if latest_checkpoint:
    print("Loading model checkpoint: {}".format(latest_checkpoint))
    saver.restore(sess, latest_checkpoint)

  # Start worker threads
  worker_threads = []
  for worker in workers:
    t = threading.Thread(target=worker.run, args = (sess,coord,FLAGS.t_max))
    t.start()
    worker_threads.append(t)

  # Start a thread for policy eval task
  # monitor_thread = threading.Thread(target=lambda: pe.continuous_eval(FLAGS.eval_every, sess, coord))
  # monitor_thread.start()

  # Wait for all workers to finish
  coord.join(worker_threads)