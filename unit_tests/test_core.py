import unittest

from context import TestCase_ext

import numpy as np

# from keras import backend_config as K
from keras import backend as K, layers as ly
from keras import activations, losses, Sequential
from keras.layers import Dense, Input
# Dense, Input = ly.Dense, ly.Input
import tensorflow as tf

from core import Functions, ActivationFunctions, XOR_forward_prop, XOR_back_prop
from constants import EPSILON, LEAKY_eps, X_BATCH_4, Y_XOR_TRUE_4

class TestFunctions(TestCase_ext):

    def test_sigmoid(self):
        """ test the sigmoid function, its value and derivative vs keras/tensorflow calculus """
        vals = np.array([-np.inf] + list(range(-20, 20)) + [np.inf])
        sigmoid = Functions.sigmoid(vals)
        result = sigmoid.value()
        keras_result = activations.sigmoid(vals).numpy()
        self.assertIterableAlmostEqual(result, keras_result, 
                                       f"test_sigmoid not passed for vals: {vals}")
        
        seed, rng = self.get_seed_rng()
        # seed = 34635
        # rng = np.random.default_rng(seed)
        vals = rng.random((10, 10), dtype=np.float64) * 40 - 20 # take 100 random values in interval (-20, 20)
        sigmoid = Functions.sigmoid(vals)
        result = sigmoid.value()
        result_derivative = sigmoid.derivative()
        
        x = tf.Variable(vals)
        # Use a GradientTape to record the operations
        with tf.GradientTape() as tape:
            y = activations.sigmoid(x)

        # Compute the gradient of y with respect to x
        dy_dx = tape.gradient(y, x)
        keras_sigmoid_derivative = dy_dx.numpy()
        
        # and now test the sigmoid derivative also:
        self.assertIterableAlmostEqual(result_derivative, keras_sigmoid_derivative, 
                                       f"test_sigmoid not passed for seed: {seed}", places=5)
        
        print(f"test_sigmoid passed for seed: {seed}")
    # end test_sigmoid

    def test_ReLU(self):
        vals = np.arange(-20, 20, 0.1)
        relu = Functions.ReLU(vals)
        result = relu.value()
        keras_result = activations.relu(vals).numpy()
        self.assertIterableAlmostEqual(result, keras_result, msg="test_ReLU not passed", places=5)

    def test_LeakyReLU(self):
        vals = np.arange(-20, 20, 0.1)
        leaky_relu = Functions.LeakyReLU(vals)
        result = leaky_relu.value()
        try:
            keras_result = activations.relu(vals, alpha=LEAKY_eps).numpy()
        except TypeError:
            keras_result = activations.relu(vals, negative_slope=LEAKY_eps).numpy()
        self.assertIterableAlmostEqual(result, keras_result, msg="test_LeakyReLU not passed", places=5)

    def test_tanh(self):
        vals = np.arange(-20, 20, 0.1)
        tanh = Functions.tanh(vals)
        result = tanh.value()
        self.assertIterableAlmostEqual(result, activations.tanh(vals).numpy())

    def test_linear(self):
        linear = Functions.linear(0)
        result = linear.value()
        self.assertIterableAlmostEqual(result, 0)

    def test_BinaryStop(self):
        binary_stop = Functions.BinaryStop(0)
        result = binary_stop.value()
        self.assertIterableAlmostEqual(result, 0)
    

    def test_LCE_Loss(self):
        """ test the LCE_Loss function, its value, cost and derivative """
        y_pred = np.concatenate(( np.zeros(1), 
                                 np.geomspace(1e-9, 0.1, num=9), # very close to 0,
                                 np.linspace(0.2, 0.8, 7), 
                                 (1 - np.geomspace(1e-9, 0.1, num=9))[::-1], # very close to 1
                                 np.ones(1)) 
                                 )
        m = y_pred.shape[0]
        y_pred = np.concatenate( (y_pred, y_pred) ) # twice for testing with y_true = 0 and 1
        y_true = np.concatenate( (np.ones(m, np.int8), np.zeros(m, np.int8)) )
        m = y_true.shape[0] # the new m aka 2*m

        y_pred = np.clip(y_pred, EPSILON, 1 - EPSILON ) # clip to avoid log(0) 
        # ----------
        # NOTE : to fit keras implementation of bce, 
        # we must add/subtract epsilon to y_pred depending on whether it will be compared with 0 or 1 
        y_pred_stable = np.where(y_true, y_pred + EPSILON, y_pred - EPSILON) 
        # ----------

        my_lce_loss_function = Functions.LCE_Loss(a = y_pred_stable, y_true = y_true)
        my_lce_value = my_lce_loss_function.value()
        my_lce_cost = my_lce_loss_function.cost()
        my_lce_derivative = my_lce_loss_function.derivative() 

        # prepare to pass them to tf
        y_true_tf = tf.convert_to_tensor(y_true.reshape((m, 1)))
        y_pred_tf = tf.convert_to_tensor(y_pred.reshape((m, 1))) 

        K.set_epsilon(EPSILON) # set the same constants.EPSILON to keras backend also
        with tf.GradientTape() as tape:
            tape.watch(y_pred_tf)
            # keras_lce_loss = tf.keras.losses.binary_crossentropy(y_true_tf, y_pred_tf) 
            keras_lce_loss = losses.binary_crossentropy(y_true_tf, y_pred_tf) 
        
        self.assertIterableAlmostEqual(my_lce_value, keras_lce_loss.numpy(), 
                                       f"test_LCE_Loss _value not passed !", places=5)
        
        self.assertIterableAlmostEqual(my_lce_cost, np.mean(keras_lce_loss.numpy(), axis=-1), 
                                       f"test_LCE_Loss _cost not passed !", places=5)

        keras_result_derivative_lce_loss = tape.gradient(keras_lce_loss, y_pred_tf)

        # self.assertIterableAlmostEqual(my_lce_derivative, keras_result_derivative_lce_loss.numpy().reshape((m, )), 
        #             f"test_LCE_Loss _derivative not passed !", places=5)
        # NOTE: this will not pass because derivative is huge on extremes ! :D
        # ----------------

        # this will pass with rtol=1e-5, atol=0
        np.testing.assert_allclose(my_lce_derivative, keras_result_derivative_lce_loss.numpy().reshape((m, )), 
                                   rtol=1e-5, atol=0,
                                   err_msg=f"test_LCE_Loss _derivative not passed !")

        print(f"test_LCE_Loss passed !")
    # end test_LCE_Loss


    def test_Hinge_Loss(self):
        """ test the Hinge_Loss function, its value, cost and derivative """
        seed, rng = self.get_seed_rng()
        # seed = 58583
        # rng = np.random.default_rng(seed)
        m = rng.integers(4, 11) # m = number of samples
        y_true = rng.choice([0, 1], m, replace=True)
        y_pred = rng.random(m, dtype=np.float64) * 20 - 10 # random values in interval (-10, 10)
        my_hinge_loss_function = Functions.Hinge_Loss(a = y_pred, y_true=y_true)
        my_hinge_value = my_hinge_loss_function.value()
        my_hinge_cost = my_hinge_loss_function.cost()
        my_hinge_derivative = my_hinge_loss_function.derivative() 
        
        _y_true = y_true.copy()
        _y_true[np.where(_y_true == 0)] = -1 # convert 0 to -1
        y_true_tf = tf.convert_to_tensor(_y_true.reshape((m, 1)))
        y_pred_tf = tf.convert_to_tensor(y_pred.reshape((m, 1))) 
        K.set_epsilon(EPSILON)
        with tf.GradientTape() as tape:
            tape.watch(y_pred_tf)
            # keras_hinge_loss = tf.keras.losses.hinge(y_true_tf, y_pred_tf) 
            keras_hinge_loss = losses.hinge(y_true_tf, y_pred_tf) 

        self.assertIterableAlmostEqual(my_hinge_value, keras_hinge_loss.numpy(), 
                                       f"test_Hinge_Loss _value not passed for seed: {seed}", places=5)
        
        self.assertIterableAlmostEqual(my_hinge_cost, np.mean(keras_hinge_loss.numpy(), axis=-1), 
                                       f"test_Hinge_Loss _cost not passed for seed: {seed}", places=5)

        keras_result_derivative_hinge_loss = tape.gradient(keras_hinge_loss, y_pred_tf)

        self.assertIterableAlmostEqual(my_hinge_derivative, keras_result_derivative_hinge_loss.numpy().reshape((m,)), 
                    f"test_Hinge_Loss _derivative not passed for seed: {seed} nb_samples = {m}", places=5)        

        print(f"test_Hinge_Loss passed for seed: {seed}")
    # end test_Hinge_Loss


    def test_Squared_Hinge_Loss(self):
        """ test the Squared_Hinge_Loss function, its value, cost and derivative """
        seed, rng = self.get_seed_rng()
        # seed = 25745
        # rng = np.random.default_rng(seed)
        m = rng.integers(4, 11) # m = number of samples
        y_true = rng.choice([0, 1], m, replace=True)
        y_pred = rng.random(m, dtype=np.float64) * 20 - 10 # random values in interval (-10, 10)
        my_hinge_loss_function = Functions.Squared_Hinge_Loss(a = y_pred, y_true=y_true)
        my_hinge_value = my_hinge_loss_function.value()
        my_hinge_cost = my_hinge_loss_function.cost()
        my_hinge_derivative = my_hinge_loss_function.derivative() 
        
        _y_true = y_true.copy()
        _y_true[np.where(_y_true == 0)] = -1 # convert 0 to -1
        y_true_tf = tf.convert_to_tensor(_y_true.reshape((m, 1)))
        y_pred_tf = tf.convert_to_tensor(y_pred.reshape((m, 1))) 
        K.set_epsilon(EPSILON)
        with tf.GradientTape() as tape:
            tape.watch(y_pred_tf)
            # keras_hinge_loss = tf.keras.losses.squared_hinge(y_true_tf, y_pred_tf) 
            keras_hinge_loss = losses.squared_hinge(y_true_tf, y_pred_tf) 

        self.assertIterableAlmostEqual(my_hinge_value, keras_hinge_loss.numpy(), 
                                       f"test_Squared_Hinge_Loss _value not passed for seed: {seed}", places=5)
        
        self.assertIterableAlmostEqual(my_hinge_cost, np.mean(keras_hinge_loss.numpy(), axis=-1), 
                                       f"test_Squared_Hinge_Loss _cost not passed for seed: {seed}", places=5)

        keras_result_derivative_hinge_loss = tape.gradient(keras_hinge_loss, y_pred_tf)

        self.assertIterableAlmostEqual(my_hinge_derivative, keras_result_derivative_hinge_loss.numpy().reshape((m,)), 
                    f"test_Squared_Hinge_Loss _derivative not passed for seed: {seed} nb_samples = {m}", places=5)  

        print(f"test_Squared_Hinge_Loss passed for seed: {seed}")
    # end test_Squared_Hinge_Loss


    def test_Hinge_Loss_0_1(self):
        """ test the Hinge_Loss_0_1 function """
        seed, rng = self.get_seed_rng()
        y_true = rng.choice([0, 1], 10, replace=True)
        y_pred = rng.random(10, dtype=np.float64) 
        _y_true = y_true.copy()
        _y_true[np.where(_y_true == 0)] = -1 # convert 0 to -1
        hinge_loss = Functions.Hinge_Loss_0_1(a=y_pred, y_true=y_true)
        result = hinge_loss.cost()
        K.set_epsilon(EPSILON)
        y_pred = y_pred * 2 - 1 # my Hinge_Loss_0_1 do that so pass the same to keras
        result_keras_hinge_loss = losses.hinge(y_true=_y_true, y_pred=y_pred).numpy()
        self.assertIterableAlmostEqual(result, result_keras_hinge_loss, 
                                       f"test_Hinge_Loss not passed for seed: {seed}")

        print(f"test_Hinge_Loss passed for seed: {seed}")
    # end test_Hinge_Loss_0_1

    def test_Squared_Hinge_Loss_0_1(self):
        """ test the Squared_Hinge_Loss_0_1 function """
        seed, rng = self.get_seed_rng()
        y_true = rng.choice([0, 1], 10, replace=True)
        y_pred = rng.random(10, dtype=np.float64) 
        _y_true = y_true.copy()
        _y_true[np.where(_y_true == 0)] = -1 # convert 0 to -1
        squared_hinge_loss = Functions.Squared_Hinge_Loss_0_1(a=y_pred, y_true=y_true)
        result = squared_hinge_loss.cost()
        K.set_epsilon(EPSILON)
        y_pred = y_pred * 2 - 1 # my Squared_Hinge_Loss_0_1 do that so pass the same to
        result_keras_squared_hinge_loss = losses.squared_hinge(y_true=_y_true, y_pred=y_pred).numpy()
        self.assertIterableAlmostEqual(result, result_keras_squared_hinge_loss, 
                                       f"test_Hinge_Loss not passed for seed: {seed}")

        print(f"test_Squared_Hinge_Loss passed for seed: {seed}")
    # end test_Squared_Hinge_Loss_0_1


class TestXORForwardProp(TestCase_ext):
    """ test the XOR_forward_prop function calculus vs keras calculus"""
    def test_XOR_forward_prop(self):
        
        activation1 = ActivationFunctions.ReLU
        activation2 = ActivationFunctions.sigmoid
        str_activation1 = activation1.__name__.lower()
        str_activation2 = activation2.__name__.lower()
                        
        seed, rng = self.get_seed_rng() # get a seed and a random number generator initialized with

        w1 = rng.random((2, 2), dtype=np.float64) * 20 - 10 # random values in interval (-10, 10) for w1
        b1 = rng.random((2, ), dtype=np.float64) * 20 - 10 # random values for bias_1 in interval (-10, 10)

        w2 = rng.random((2, 1), dtype=np.float64) * 20 - 10 # random values in interval (-10, 10) for w2
        b2 = rng.random((1, ), dtype=np.float64) * 20 - 10 # random values for bias_2 in interval (-10, 10)

        x = X_BATCH_4 # the batch of 4 possible XOR samples

    # keras calculus for the forward propagation
        # Create the Dense layers
        dense1 = Dense(2, activation=str_activation1, weights=[w1, b1])
        dense2 = Dense(1, activation=str_activation2, weights=[w2, b2])

        # Manually apply the layers to get a1 and a2
        expected_a1 = dense1(x).numpy()
        expected_a2 = dense2(expected_a1).numpy()
    
    # my calculus of the forward propagation
        w1_b = np.vstack((w1, b1.reshape(1, 2))) # append bias 1
        w2_b = np.vstack((w2, b2.reshape(1, 1))) # append bias 2 

        a1, a2 = XOR_forward_prop(x, w1_b, activation1, w2_b, activation2)

    # compare the results
        np.testing.assert_allclose(a1, expected_a1, atol=1e-5, 
                                   err_msg=f"test_XOR_forward_prop not passed for a1 / seed: {seed}")
        np.testing.assert_allclose(a2, expected_a2, atol=1e-5, 
                                   err_msg=f"test_XOR_forward_prop not passed for a2 / seed: {seed}")

        print(f"test_XOR_forward_prop passed for seed: {seed}")

# end test_XOR_forward_prop


class TestXORBackProp(TestCase_ext):
    """ test the XOR_back_prop calculus vs keras/tensorflow calculus"""
    def test_XOR_back_prop(self):

        activation1 = ActivationFunctions.ReLU
        activation2 = ActivationFunctions.sigmoid
        str_activation1 = activation1.__name__.lower()
        str_activation2 = activation2.__name__.lower()
        
        seed, rng = self.get_seed_rng()
        # seed = 37380
        # rng = np.random.default_rng(seed)
        w1 = rng.random((2, 2), dtype=np.float64) * 20 - 10 # random values in interval (-10, 10) for w1
        b1 = rng.random((2, ), dtype=np.float64) * 20 - 10 # random values for bias_1 in interval (-10, 10)
        w2 = rng.random((2, 1), dtype=np.float64) * 20 - 10 # random values in interval (-10, 10) for w2
        b2 = rng.random((1, ), dtype=np.float64) * 20 - 10 # random values for bias_2 in interval (-10, 10)

        w2_b2 = np.vstack((w2, b2.reshape(1, 1))) # append bias 2

        _slice = rng.choice([0, 1, 2, 3], rng.integers(6, 11), replace=True)
        x = X_BATCH_4[_slice] # the batch of 4 possible XOR samples
        y_true = Y_XOR_TRUE_4[_slice]
        m = x.shape[0] # m = number of samples

    # keras calculus for the forward propagation
        # Create the Dense layers
        dense1 = Dense(2, activation=str_activation1, weights=[w1, b1])
        dense2 = Dense(1, activation=str_activation2, weights=[w2, b2])
        # Manually apply the layers to get a1 and a2
        a1 = dense1(x).numpy()
        a2 = dense2(a1).numpy()
        fctLoss = Functions.LCE_Loss

    # my calculus of the back propagation
        dw1, dw2 = XOR_back_prop(x, activation1, a1, w2_b2, activation2, a2, y_true, fctLoss)

    # keras calculus for the forward propagation
        model = Sequential() # Create the model
        model.add(Input(shape=(2, ))) # Add an Input layer
        model.add(dense1) # Add the first Dense layer
        model.add(dense2) # Add the second Dense layer
        model.compile(optimizer='adam', loss='binary_crossentropy') # Compile the model

        with tf.GradientTape() as tape:
            y_pred = model(x) # Forward pass
            # loss = tf.keras.losses.binary_crossentropy(y_true, y_pred) # Compute the loss
            loss = losses.binary_crossentropy(y_true, y_pred) # Compute the loss
        
        gradients = tape.gradient(loss, model.trainable_weights)

        expected_dw1 = gradients[0].numpy() / m
        expected_db1 = gradients[1].numpy() / m
        expected_dw2 = gradients[2].numpy() / m
        expected_db2 = gradients[3].numpy() / m
        
    # compare the results
        # and print some info for debug reproducibility
        np.testing.assert_allclose(dw1, np.vstack((expected_dw1, expected_db1)), atol=1e-5, 
                                err_msg=f"test_XOR_back_prop not passed for dw1 / seed: {seed} (nb/batch = {m}, batch = {_slice})")
        np.testing.assert_allclose(dw2, np.vstack((expected_dw2, expected_db2)), atol=1e-5,    
                                err_msg=f"test_XOR_back_prop not passed for dw2 / seed: {seed} (nb/batch = {m}, batch = {_slice})")
        # and print some info just to see what test passed
        print(f"test_XOR_back_prop passed for seed: {seed} (nb/batch = {m}, batch = {_slice})")

# end test_XOR_back_prop

        
if __name__ == '__main__':
    unittest.main()
