# core.py
"""
This module defines functions used in neural networks, activation functions, loss functions.
Also the Forward and Backward propagation.
"""

import numpy as np
from numpy import where
from enum import Enum, member, Flag, auto, nonmember
from typing import Any, Type, Optional, Dict
from abc import ABC, abstractmethod

from constants import NBSP, EPSILON, LEAKY_eps


# region Functions

class FunctionType(Flag):
    HiddenLayer = auto()
    OutputLayer = auto()
    Loss = auto()

class Function_d1(ABC):
    """ Function with first derivative interface: value = f(x), derivative() = f'(x) or derivative(a) = f'(a=f(x)) """
    @abstractmethod
    def __init__(self, *args):
        pass

    @classmethod
    def toolTip_as_html(cls):
        if cls.__doc__:
            return cls.__doc__.replace('\n', '<br>')
        return cls.__name__

    @classmethod
    def fType(cls)-> FunctionType:
        raise NotImplementedError(f"fType(cls) -> FunctionType: must be implemented for {cls.__name__}") 
        pass

    @abstractmethod
    def value(self) -> Any:
        pass
    
    @abstractmethod
    def derivative(self, *args) -> Any:
        pass
# end class Function_d1

class Function_d1_cost(Function_d1):
    """ Interface: Function_d1 + cost = """
    @abstractmethod
    def cost(self) -> Any:
        pass
# end class Function_d1_cost

class Functions():

    class sigmoid(Function_d1):
        """ Logistic (Sigmoid) 
            on derivative: 
            clip(0 + EPSILON, 1 - EPSILON) 
            to fit with LCE """ 
        
        @classmethod
        def toolTip_as_html(cls):
            return super().toolTip_as_html() + f"<br>{NBSP*3} <i> (EPSILON = {str(EPSILON)}) </i>"
        
        def __init__(self, x):
            self._x = x

        def value(self):
                # to avoid RuntimeWarning: overflow encountered in exp
            v = np.exp(np.fmin(self._x, 0)) / (1 + np.exp(-np.abs(self._x)))
            return v

        def derivative(self, a:Optional[Any] = None):
            """ if a is None do a = Ꟙ(self._x), else use a as Ꟙ(x) """
            if a is None:
                a = self.value()
            try:
                # a is value of sigmoid so must be in [0, 1] but actually without extreme values, so clip in (0, 1)
                a = a.clip(0 + EPSILON, 1 - EPSILON)
            except AttributeError:
                a = min(a, max(a, 0 + EPSILON), 1 - EPSILON)
            return a * (1 - a)
        
        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.HiddenLayer | FunctionType.OutputLayer
    # end class sigmoid

    class ReLU(Function_d1):
        """ Rectified Linear Unit (ReLU) """

        def __init__(self, x):
            self._x = x

        def value(self):
            # return max(0, x) 
            return self._x * (self._x > 0)
        
        def derivative(self, a:Optional[Any] = None):
            if a is None:
                a = self.value()
            # return (0. + (a >= 0)) 
            # In TensorFlow's implementation of the ReLU activation function, the derivative at 0 is considered to be 0. 
                # This is a design choice made for the sake of simplicity and computational efficiency.
                # So, when you use tf.keras.layers.Dense( , activation='relu'), during backpropagation, 
                # the derivative of the ReLU function at 0 will be treated as 0.
            return (0. + (a > 0)) # strictly greater than 0

        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.HiddenLayer | FunctionType.OutputLayer
    # end class ReLU

    class LeakyReLU(Function_d1):
        """ Leaky Rectified Linear Unit """

        @classmethod
        def toolTip_as_html(cls):
            return super().toolTip_as_html() + f"<br> {NBSP*3} <i> (LEAKY_eps = {str(LEAKY_eps)} ) </i>"

        def __init__(self, x):
            self._x = x
        def value(self):
            return self._x * (self._x > 0) + LEAKY_eps * self._x * (self._x < 0)
        def derivative(self, a:Optional[Any] = None):
            if a is None:
                a = self.value()
            # return (0. + (a >= 0)) + (LEAKY_eps * (a < 0))
            # In TensorFlow's implementation of the ReLU activation function, the derivative at 0 is considered to be 0... 
            return (0. + (a > 0)) + (LEAKY_eps * (a < 0))
 
        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.HiddenLayer 
    # end class LeakyReLU
   
    class tanh(Function_d1):
        """ Hyperbolic Tangent (Tanh) """
        def __init__(self, x):
            self._x = x

        def value(self):
            return (np.tanh(self._x))
            
        def derivative(self, a:Optional[Any] = None):
            if a is None:
                a = self.value()
            return (1 - a * a)

        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.HiddenLayer | FunctionType.OutputLayer 
    # end class tanh

    class linear(Function_d1):
        def __init__(self, x):
            self._x = x
        def value(self):
            return self._x
        def derivative(self, _any):
            return np.ones_like(self._x)

        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.HiddenLayer | FunctionType.OutputLayer
    
    class BinaryStop(Function_d1):
        def __init__(self, x):
            self._x = x
        def value(self):
            return (self._x > 0) * 1
        def derivative(self, _):
            return np.zeros_like(self._x) # <=> self._x * 0 = [0, 0, ], meaning STOP

        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.OutputLayer
        

    class LCE_Loss(Function_d1_cost):
        """ LCE (Log cross-entropy)
            to avoid log(0)
            clip(0 + EPSILON, 1 - EPSILON) """
        @classmethod
        def toolTip_as_html(cls):
            return super().toolTip_as_html() + f"<br> {NBSP*3} <i> (EPSILON = {str(EPSILON)}) </i>"
        
        def __init__(self, a, y_true):
            try:
                self._a = a.clip(0 + EPSILON, 1 - EPSILON) # to avoid log(0) 
            except AttributeError:
                self._a = min(a, max(a, 0 + EPSILON), 1 - EPSILON)            
            self._y_true = np.copy(y_true)

        def value(self) -> np.ndarray:
            v = np.ones_like(self._a)
            try:
                v = - (self._y_true * np.log(self._a) + (1 - self._y_true) * np.log(1 - self._a)) 
            except Exception as ex:
                print("loss exception: ", ex, "for _a:",  self._a, "_y_true :", self._y_true)
            return v
        
        def cost(self):
            ret = np.mean(self.value(), axis=-1)
            return ret

        def derivative(self):
            """ dL/da for y_true"""
            return - (
                self._y_true / self._a + (self._y_true - 1) / (1 - self._a)
                )

        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.Loss
    # end class LCE_Loss
        
    class Hinge_Loss(Function_d1_cost):
        """ Hinge Loss input [-1, 1]
            mapping y_true {0, 1}->{-1, 1} 
            using after: 
            Hidden Layer = ReLU / tanh
            Output Layer = linear"""

        def __init__(self, a, y_true):
            self._a = a 

            # y_true {0, 1} -> {-1, 1}
            self._y_true = np.copy(y_true)  # == self._y_true = y_true - (y_true == 0)
            self._y_true[where(self._y_true == 0)] = -1 

        def value(self) -> np.ndarray:
            v = np.maximum(0, 1 - self._y_true * self._a)
            return v
            
        def cost(self):
            c = np.mean(self.value(), axis=-1)
            return c
        
        def derivative(self):
            """ dL/da for y_true"""
            d = -self._y_true * (self._y_true * self._a < 1)
            return d
        
        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.Loss
    # end class Hinge_Loss 

    class Squared_Hinge_Loss(Function_d1_cost):
        """ <b>Squared</b> Hinge Loss input [-1, 1]
            mapping y_true {0, 1}->{-1, 1} 
            using after: 
            Hidden Layer = ReLU / tanh
            Output Layer = linear"""
        def __init__(self, a, y_true):
            self._a = a

            # y_true {0, 1} -> {-1, 1}
            self._y_true = np.copy(y_true) 
            self._y_true[where(self._y_true == 0)] = -1 


        def value(self) -> np.ndarray:
            v = (np.maximum(0, 1 - self._y_true * self._a)) ** 2
            return v
            
        def cost(self):
            c = np.mean(self.value(), axis=-1)
            return c
        
        def derivative(self):
            """ dL/da for y_true """
            d = -2 * self._y_true * np.maximum(0 , 1 - self._y_true * self._a )
            return d
        
        @staticmethod
        def fType() -> FunctionType:
            return FunctionType.Loss
    # end class Squared_Hinge_Loss

    class Hinge_Loss_0_1(Hinge_Loss):
        """ Hinge Loss input [0-1]
            mapping [0, 1]->[-1, 1]
            and y_true {0, 1}->{-1, 1} """

        def __init__(self, a, y_true):
            super().__init__(a, y_true)
            # and scaling and shifting values [0, 1] -> [-1, 1]
            self._a = a * 2 - 1

    class Squared_Hinge_Loss_0_1(Squared_Hinge_Loss):
        """ <b>Squared</b> Hinge Loss input [0, 1]
        mapping [0, 1]->[-1, 1]
        and y_true {0, 1}->{-1, 1} """

        def __init__(self, a, y_true):
            # scaling and shifting values a=y_pred from [0, 1] -> [-1, 1]
            super().__init__(a, y_true)
            self._a = a * 2 - 1
# end class Functions

class ActivationFunctions:
    sigmoid = Functions.sigmoid
    ReLU = Functions.ReLU
    LeakyReLU = Functions.LeakyReLU
    tanh = Functions.tanh
    linear = Functions.linear
    BinaryStop = Functions.BinaryStop

class LossFunctions:    
    LCE_Loss = Functions.LCE_Loss
    Hinge_Loss = Functions.Hinge_Loss
    Squared_Hinge_Loss = Functions.Squared_Hinge_Loss
    Hinge_Loss_0_1 = Functions.Hinge_Loss_0_1
    Squared_Hinge_Loss_0_1 = Functions.Squared_Hinge_Loss_0_1
    
class FunctionsListsByType:
    HiddenLayer:Dict[str, Type[Function_d1]] = { k: v for k, v in Functions.__dict__.items() 
                                                if (isinstance(v, type) and 
                                                    issubclass(v, Function_d1) and 
                                                    FunctionType.HiddenLayer in v.fType()
                                                    ) 
                                                }
    OutputLayer:Dict[str, Type[Function_d1]] = { k: v for k, v in Functions.__dict__.items() 
                                                if (isinstance(v, type) and 
                                                    issubclass(v, Function_d1) and
                                                    FunctionType.OutputLayer in v.fType()
                                                    )
                                                }
    LossFunction:Dict[str, Type[Function_d1_cost]] = { k: v for k, v in Functions.__dict__.items()
                                                    if (isinstance(v, type) and 
                                                        issubclass(v, Function_d1_cost) and
                                                        FunctionType.Loss in v.fType()
                                                        )   
                                                    }

# endregion Functions

# region Forward / backward propagation
def XOR_forward_prop(x, w1, activation1:Type[Function_d1], w2, activation2:Type[Function_d1]):
    """ Forward propagation: compute and return a1, a2 """
    # m rows in batch => 2 columns(x0, x1) and m rows
    m = x.shape[0]          

    # (+1)=bias => 3 columns (x0, x1, +1) and m rows
    x_b = np.hstack((x, np.ones(shape=(m, 1)))) 

    # (m, 3) .dot (3, 2) = (m, 2)
    z1 = x_b @ w1       # z1 = np.dot(w1, x)

    # activation of hidden layer 
    a1 = activation1(z1).value() 

    # (+1)=bias => 3 columns (a1_0, a1_1, +1) and m rows
    a1_b = np.hstack((a1, np.ones(shape=(m, 1)))) 

    # (m, 3) .dot (3, 1) = (m, 1)
    z2 = a1_b @ w2      
    
    # activation of output layer
    a2 = activation2(z2).value()

    return a1, a2 # a1 = hidden layer, a2 = output layer = y_hat
# end XOR_forward_prop

# Backward propagation
def XOR_back_prop(x, activation1:Type[Function_d1], a1,
                  w2, activation2:Type[Function_d1], a2, 
                  y_true, fctLoss:Type[Function_d1] = Functions.LCE_Loss
                  ):
    
    m = a1.shape[0] # m rows in batch

    loss_a2 = fctLoss(a2, y_true) # ex fctLoss = LCE_Loss (aka binary_crossentropy in tf)
    dLoss_da2 = loss_a2.derivative() # shape (m, 1)
    da2_dz2 = activation2(a2).derivative(a2)  #  shape (m, 1)  for ex a2 = sigmoid(z2) => sigmoid.derivative(a2) = sigmoid(a2) * (1 - sigmoid(a2))
    
    # The gradient of z2 with respect to w2, b2, and a1 is 
        # dz2/dw2 = a1, dz2/db2 = 1, dz2/da1 = w2, (where z2 = a1 * w2 + b2)
    a1_b = np.hstack((a1, np.ones(shape=(m, 1)))) # shape (m, 3)
    dz2_dw2 = a1_b # shape (m, 3) 
    
    # Now the gradient of the loss with respect to w2 is :
    # dloss/dw2 = dloss/da2 * da2/dz2 * dz2/dw2.
    dLoss_dw2 = np.dot(dz2_dw2.T, dLoss_da2 * da2_dz2) / m # shapes (3, m) @ (m, 1) => shape (3, 1) aka shape W2(bias included)
        # the calculated gradient is divided by m, which is the number of samples in the batch. 
        # This is effectively calculating the average gradient over all samples in the batch.

    dz2_da1 = w2[:-1] # shape (2, 1) (bias excluded)
    dLoss_da1 = np.dot(dLoss_da2 * da2_dz2, dz2_da1.T) # shape (m, 1) * (1, 2) = (m, 2)
    da1_dz1 = activation1(a1).derivative(a1) # shape (m, 2) for ex a1 = relu(z1) => relu.derivative(a1) = 0 + (a1 > 0)
    x_b = np.hstack((x, np.ones((m, 1)))) # shape (m, 3) +1 for bias
    dz1_dw1 = x_b # shape (m, 3)

    dLoss_dw1 = np.dot(dz1_dw1.T, dLoss_da1 * da1_dz1) / m # shape (3, m) @ (m, 2) => (3, 2) aka shape W1(bias included)

    return dLoss_dw1, dLoss_dw2
# end XOR_back_prop

# endregion Forward / backward propagation


if __name__ == '__main__':
    print(Functions.sigmoid(1))
    print(Functions.sigmoid.fType())
    print(Functions.sigmoid(1).toolTip_as_html())
    print(Functions.sigmoid(1).value())
    print(Functions.sigmoid(1).derivative(1))
    print(Functions.sigmoid(1).derivative())

    print(FunctionsListsByType.HiddenLayer)
    print(FunctionsListsByType.OutputLayer)
    print(FunctionsListsByType.LossFunction)
    print(FunctionType.HiddenLayer.value)
    print(FunctionType.OutputLayer.value)
    print(FunctionType.Loss.value)

    print(FunctionsListsByType.HiddenLayer["sigmoid"])
    
    print( issubclass(FunctionsListsByType.HiddenLayer["sigmoid"], Function_d1) )
    
    print( FunctionsListsByType.HiddenLayer["sigmoid"] is Functions.sigmoid)

    print( type(FunctionsListsByType.HiddenLayer["sigmoid"]))
