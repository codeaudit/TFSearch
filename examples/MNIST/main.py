"""
Another slightly more complex example involving the benchmark MNIST dataset
The goal here is to evolve the weights and biases for MNIST
This main script uses Network to convert genotype-phenotype and to evaluate
fitness
Author: Madhavun Candadai
Date Created: Sep 18, 2017
"""

import numpy as np
import tensorflow as tf
import scipy.misc
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

from tensorflow.examples.tutorials.mnist import input_data
from params import *
from TFSearch import *
from NetworkPop import *


def learn_mnist():
    # initialize a population
    thisPop = np.random.uniform(
        size=(EVOL_P["pop_size"], EVOL_P["genotype_size"]),
        low=EVOL_P["genotype_min_val"],
        high=EVOL_P["genotype_max_val"],
    )

    # create TensorFlow session
    sess = tf.Session()

    # creating objects for running the corresponding graphs
    tfs = TFSearch(EVOL_P)  # graph TFsearch.py for producing new population

    mnist = input_data.read_data_sets("MNIST_data/", one_hot=True)

    print("\nStarting to run session")
    fitnessess = []
    print(["Generation", "Best Fitnesss", "Mean Fitness"])

    with NetworkPop(EVOL_P) as nets:
        for gen in range(EVOL_P["maxGens"]):
            inputs_, y_ = mnist.train.next_batch(EVOL_P["numSamples"])
            y_ = [np.argmax(y_, 1)]

            # Given a population, first compute fitness using the user defined graph, Generation_Life
            fs = sess.run(nets.fitness, {pop_pl: thisPop, ins: inputs_, ys: y_})
            for _ in range(EVOL_P["numTrials"] - 1):
                inputs_, y_ = mnist.train.next_batch(EVOL_P["numSamples"])
                y_ = [np.argmax(y_, 1)]
                fs += sess.run(nets.fitness, {pop_pl: thisPop, ins: inputs_, ys: y_})
            fs /= EVOL_P["numTrials"]
            fitnessess.append(np.max(fs))

            # printing out some stats occasionally
            if gen == 0 or (gen + 1) % 100 == 0:
                bestFs = np.max(fs)
                meanFs = np.mean(fs)
                print(gen + 1, bestFs, meanFs)

            # Producing a new population given this population and its fitnesss using Generation_Reproduce
            thisPop = sess.run(tfs.generation_step, {pop_pl: thisPop, fits_pl: fs})

    # Now with test images
    print("\n\nTesting final best...Fitness=", end=" ")
    inputs_ = mnist.test.images  # [:EVOL_P['numSamples'],:]
    y_ = mnist.test.labels  # [:EVOL_P['numSamples'],:]
    y_ = [np.argmax(y_, 1)]
    EVOL_P["numSamples"] = np.shape(inputs_)[0]
    with NetworkPop(EVOL_P) as nets:
        fs = sess.run(nets.fitness, {pop_pl: thisPop, ins: inputs_, ys: y_})
        print(fs[0], "\n\n")

    return fitnessess


if __name__ == "__main__":
    for r in range(5):
        fits = learn_mnist()
        np.save("./results/fits_{}.npy".format(r), fits)
        plt.plot(fits)
    plt.xlabel("Generations")
    plt.ylabel("Fitness")
    plt.savefig("./results/fitsvsGens.png")
