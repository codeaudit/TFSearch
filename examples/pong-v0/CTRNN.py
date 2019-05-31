"""
This CTRNN_popSim class implements a fully-vectorized Tensorflow implementation of
1. genotype-phenotype conversion
2. euler step the CTRNN
with the whole population of networks data-typed as a single matrix.
Author: Madhavun Candadai
Date Created: Sep 23, 2017
"""
import numpy as np
import tensorflow as tf
from params import *

# Changing states and outputs to vars - but using for re-initializing
state_pl = tf.placeholder(tf.float32, shape=(None, None), name="rand_states")
output_pl = tf.placeholder(tf.float32, shape=(None, None), name="rand_outputs")
# input_pl = tf.placeholder(tf.float32,shape=(None,None),name='input_t')


class CTRNN:
    def __enter__(self):
        return self

    def __init__(self, EVOL_P):
        """
        This CTRNN class instantiates the computational graph for the network

        Args:
        EVOL_P - a dict with required params
            'genotype_size' = scalar: dimensionality of genotype,
            'cns_size' = scalar: number of neurons in the network,
            'pop_size' = scalar: number of individuals,
            'scaling_high' = vector (1 X genotype_size): upper bound to scale genotype,
            'scaling_low' = vector (1 X genotype_size): lower bound to scale genotype,
            'step_size' = scalar: euler integration step size
        state_pl - placeholder for state at previous time step
        output_pl - placeholder for output at previous time step

        Output:
        Graph compute of
            'step_state' returns state at next time step
            'step_output' returns output at next time step
        """
        self.genotype_size = EVOL_P["genotype_size"]
        self.cns_size = EVOL_P["cns_size"]
        self.pop_size = EVOL_P["pop_size"]
        self.scaling_high = EVOL_P["scaling_high"]
        self.scaling_low = EVOL_P["scaling_low"]
        self.step_size = EVOL_P["step_size"]
        self.obs_size = EVOL_P["obs_size"]
        # self.input_pl = input_pl # current input # changed to variable
        self.device = EVOL_P["device"]

        # name_scope('CTRNN_utils'):
        # creating phenotypic vars
        with tf.device(self.device), tf.variable_scope("phenotypes", reuse=None):
            weights_T = tf.get_variable(
                "weights_T",
                dtype=tf.float32,
                shape=(self.cns_size, self.cns_size * self.pop_size),
                trainable=False,
            )
            biases_T = tf.get_variable(
                "biases_T",
                dtype=tf.float32,
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
            )
            taus_T = tf.get_variable(
                "taus_T",
                dtype=tf.float32,
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
            )
            in_weights = tf.get_variable(
                "in_weights",
                dtype=tf.float32,
                shape=(self.cns_size, self.obs_size * self.pop_size),
                trainable=False,
            )
            out_weights = tf.get_variable(
                "out_weights",
                dtype=tf.float32,
                shape=(self.pop_size, self.cns_size),
                trainable=False,
            )

        # creating vars for simulation
        with tf.device(self.device), tf.variable_scope("CTRNN_vars", reuse=None):
            state_v = tf.get_variable(
                "this_states",
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
                initializer=tf.random_uniform_initializer(minval=0, maxval=1),
            )

            output_v = tf.get_variable(
                "this_outputs",
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
                initializer=tf.random_uniform_initializer(minval=0, maxval=1),
            )

            inputs_v = tf.get_variable(
                "this_inputs", shape=(1, self.obs_size * self.pop_size), trainable=False
            )

        # def randomize_states(self):
        with tf.name_scope("randomize_ctrnns"):
            with tf.device(self.device), tf.variable_scope("CTRNN_vars", reuse=True):
                self.randomize_states = tf.assign(
                    tf.get_variable("this_states"), state_pl, name="randomizing_states"
                )
                self.randomize_outputs = tf.assign(
                    tf.get_variable("this_outputs"),
                    output_pl,
                    name="randomizing_outputs",
                )

        # name_scope('Make_CTRNNs'):
        with tf.device(self.device), tf.variable_scope("phenotypes", reuse=True):
            # get variables
            weights_v = tf.get_variable(
                "weights_T",
                dtype=tf.float32,
                shape=(EVOL_P["cns_size"], EVOL_P["cns_size"] * EVOL_P["pop_size"]),
                trainable=False,
            )
            biases_v = tf.get_variable(
                "biases_T",
                dtype=tf.float32,
                shape=(1, EVOL_P["cns_size"] * EVOL_P["pop_size"]),
                trainable=False,
            )
            taus_v = tf.get_variable(
                "taus_T",
                dtype=tf.float32,
                shape=(1, EVOL_P["cns_size"] * EVOL_P["pop_size"]),
                trainable=False,
            )
            in_weights_v = tf.get_variable(
                "in_weights",
                dtype=tf.float32,
                shape=(EVOL_P["cns_size"], EVOL_P["obs_size"] * EVOL_P["pop_size"]),
                trainable=False,
            )
            out_weights_v = tf.get_variable(
                "out_weights",
                dtype=tf.float32,
                shape=(EVOL_P["pop_size"], EVOL_P["cns_size"]),
                trainable=False,
            )

        with tf.variable_scope("population", reuse=True):
            self.pop_pl = tf.get_variable(
                "pop",
                dtype=tf.float32,
                shape=(self.pop_size, self.genotype_size),
                trainable=False,
            )

        with tf.name_scope("genotype_to_phenotype"):
            phens = (
                self.pop_pl * (self.scaling_high - self.scaling_low) + self.scaling_low
            )

            # split phens into its components - each component has the values for the whole pop
            pop_taus, pop_biases, pop_weights, in_weights, out_weights = tf.split(
                phens,
                [
                    self.cns_size,
                    self.cns_size,
                    self.cns_size ** 2,
                    self.obs_size * self.cns_size,
                    self.cns_size,
                ],
                axis=1,
            )

            # reshape them as required into 1-D vectors but 1X(cns_size*pop_size)
            self.tau_matrices = tf.assign(
                taus_v, tf.reshape(pop_taus, [1, self.cns_size * self.pop_size])
            )
            self.bias_matrices = tf.assign(
                biases_v, tf.reshape(pop_biases, [1, self.cns_size * self.pop_size])
            )

            self.weight_matrices = tf.assign(
                weights_v,
                tf.squeeze(
                    tf.transpose(
                        tf.reshape(
                            pop_weights,
                            [1, self.cns_size * self.pop_size, self.cns_size],
                        ),
                        perm=[0, 2, 1],
                    )
                ),
            )
            self.weight_matrices_s = tf.shape(self.weight_matrices)

            self.in_weight_matrices = tf.assign(
                in_weights_v,
                tf.squeeze(
                    tf.transpose(
                        tf.reshape(
                            in_weights,
                            [1, (self.obs_size * self.pop_size), self.cns_size],
                        ),
                        perm=[0, 2, 1],
                    )
                ),
            )

            self.out_weight_matrices = tf.assign(out_weights_v, out_weights)

        # name_scope('CTRNNs'):
        # retrive phenotypic variables that were set by MakeCTRNN
        with tf.device(self.device), tf.variable_scope("phenotypes", reuse=True):
            self.weights_T = tf.get_variable(
                "weights_T",
                dtype=tf.float32,
                shape=(self.cns_size, self.cns_size * self.pop_size),
                trainable=False,
            )
            self.biases_T = tf.get_variable(
                "biases_T",
                dtype=tf.float32,
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
            )
            self.taus_T = tf.get_variable(
                "taus_T",
                dtype=tf.float32,
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
            )
            self.in_weights = tf.get_variable(
                "in_weights",
                dtype=tf.float32,
                shape=(self.cns_size, self.obs_size * self.pop_size),
                trainable=False,
            )
            self.out_weights = tf.get_variable(
                "out_weights",
                dtype=tf.float32,
                shape=(self.pop_size, self.cns_size),
                trainable=False,
            )

        # reading vars for simulation
        with tf.device(self.device), tf.variable_scope("CTRNN_vars", reuse=True):
            self.state_v = tf.get_variable(
                "this_states", shape=(1, self.cns_size * self.pop_size), trainable=False
            )
            self.output_v = tf.get_variable(
                "this_outputs",
                shape=(1, self.cns_size * self.pop_size),
                trainable=False,
            )
            self.input_v = tf.get_variable(
                "this_inputs", shape=(1, self.obs_size * self.pop_size), trainable=False
            )

        with tf.name_scope("step_state"):
            # computing the total input from other neurons
            tiled_past_outputs = tf.tile(
                self.output_v, [self.cns_size, 1]
            )  # this is now cns_size X (cns_size*pop_size)
            spot_inputs = tf.multiply(
                tiled_past_outputs, self.weights_T
            )  # this now has, at each spot, one weighted input line
            rearr_spot_inputs = tf.concat(
                tf.split(spot_inputs, [self.cns_size] * self.pop_size, axis=1), axis=0
            )  # rearranged spot_inputs
            inputs = tf.expand_dims(
                tf.reduce_sum(rearr_spot_inputs, axis=1), axis=0
            )  # this is now 1 X (cns_size*pop_size)

            # computing the total external inputs
            tiled_ex_inputs = tf.tile(self.input_v, [self.cns_size, 1])
            spot_ex_inputs = tf.multiply(tiled_ex_inputs, self.in_weights)
            rearr_spot_ex_inputs = tf.concat(
                tf.split(spot_ex_inputs, [self.obs_size] * self.pop_size, axis=1),
                axis=0,
            )
            external_inputs = tf.expand_dims(
                tf.reduce_sum(rearr_spot_ex_inputs, axis=1), axis=0
            )

            # updating states
            state_update = self.state_v + self.step_size * (
                tf.multiply(inputs + external_inputs - self.state_v, 1 / self.taus_T)
            )
            self.step_state = tf.assign(self.state_v, state_update)

        with tf.name_scope("step_output"):
            # compute output for whole pop
            self.step_output = tf.assign(
                self.output_v, tf.sigmoid(self.state_v + self.biases_T)
            )
            self.control_outputs = tf.sigmoid(
                tf.reduce_sum(
                    tf.multiply(
                        tf.reshape(self.output_v, [self.pop_size, self.cns_size]),
                        self.out_weights,
                    ),
                    1,
                )
            )

    def __exit__(self, *err):
        pass