import numpy as np
import matplotlib.pyplot as plt
import IPython.display as ipd
import time

class NeuralNetwork:
    def __init__(self, n_inputs, n_hidden_units_per_layer,  n_outputs_or_class_names):

        self.debug = False  

        self.n_inputs = n_inputs
        

        self.hiddens = n_hidden_units_per_layer
        self.n_hidden_layers = len(self.hiddens)
        self.epochs = None

        if isinstance(n_outputs_or_class_names, int):
            self.classifier = False
            self.n_outputs = n_outputs_or_class_names
        else:
            self.classifier = True
            self.classes = np.array(n_outputs_or_class_names).reshape(-1,1)
            self.n_outputs = len(n_outputs_or_class_names)
        
        self.weights = []
        # Set weights using wrapper function unless there are no hidden layers. 
        if self.n_hidden_layers == 0:
            self.weights = [self._make_W(self.n_inputs, self.n_outputs)]
        else:
            self._weights_wrapper()
        
        if self.debug:
            for layeri, W in enumerate(self.weights):
                print(f'Layer {layeri + 1}: {W.shape=}')

        # Target Dictionary 
        self.target_dict = {
            "JUB66_RFP": 0,
            "JUB66_RFP_IN_CEMBIO": 1,
            "MK_JUB66_RFP_IN_JUB66": 2
        }
        
        #IV is saved as a class variables so it can easily be shared by fprop and bprop. 
        self.iv = None

        self.Hs = []
        self.mse_trace = []
        self.percent_correct_trace = []

        self.X_means = None
        self.X_stds = None
        self.T_means = None
        self.T_stds = None
    def __repr__(self):
        s = f'NeuralNetwork({self.n_inputs}, {self.hiddens}, '
        if self.classifier:
            s += f'{self.classes})'
            kind = 'classification'
        else:
            s += f'{self.n_outputs})'
            kind = 'regression'
        if self.epochs == 0:
            s += f'\n Not trained yet on a {kind} problem.'
        else:
            s += f'\n Trained on a {kind} problem for {self.epochs} epochs '
            if self.classifier:
                s += f'with a final training percent correct of {self.percent_correct_trace[-1]:.2f}.'
            else:
                s += f'with a final training MSE of {self.mse_trace[-1]:.4g}.'
        return s

    def __str__(self):
        return self.__repr__()
    
    def set_debug(self, true_false):
        self.debug = true_false
    
    def _weights_wrapper(self):
        self.weights.append(self._make_W(self.n_inputs, self.hiddens[0]))
        for i in range(self.n_hidden_layers - 1):
            self.weights.append(self._make_W(self.hiddens[i], self.hiddens[i+1]))
        self.weights.append(self._make_W(self.hiddens[-1],self.n_outputs))

    def _make_W(self, ni, nu):
        return np.random.uniform(-1, 1, size=(ni + 1, nu)) / np.sqrt(ni + 1)

    def train(self, X, T, n_epochs, learning_rate):
        if self.debug:
            print('----------Starting train()')
            
        learning_rate = learning_rate / X.shape[0]

        if self.debug:
            print(f'Adjusted {learning_rate=}')
            

        X = self._standardizeX(X)
        if self.classifier:
            self.iv = self._make_indicator_vars(T)


        for epoch in range(n_epochs):
            #Forward Prop
            if self.classifier:
                Y_classes, Y = self._fprop(X)
            else:
                Y = self._fprop(X)
            #Backward Prop
            if self.classifier:
                self._bprop(X, Y, learning_rate)
            else:
                self._bprop(X, Y, learning_rate, target=self._standardizeT(T))

            if self.classifier:
                self.mse_trace.append(self._E(X, self.iv))
                self.percent_correct_trace.append(self.percent_correct(T, Y_classes))
            else:
                self.mse_trace.append(self._E(X, T))

            if (epoch + 1) % 20 == 0:
                ipd.clear_output(wait=True)
                fig = self.plot_clusters(T)
                plt.show()
                ipd.display(fig)
                time.sleep(1)
            
        self.epochs = n_epochs

    def use(self, X, standardized=False):
        if not standardized:
            X = self._standardizeX(X)

        if self.classifier:
            Y_classes, Y_softmax = self._fprop(X)
            return Y_classes, Y_softmax
        else:
            Y = self._fprop(X)
            return self._unstandardizeT(Y)


    def _fprop(self, X):
        self.Hs = [X]
        self.Hs.append(self._f(self._add_ones(X) @ self.weights[0]))

        for i in range(1,len(self.weights)-1):
            self.Hs.append(self._f(self._add_ones(self.Hs[-1]) @ self.weights[i]))

        #Takes care of edge case of 0 hidden layers. 
        if self.n_hidden_layers == 0:
            Y = self.Hs[-1]
        else:
            Y = self._add_ones(self.Hs[-1]) @ self.weights[-1]

        if self.classifier:
            Y_softmax = self._softmax(Y)
            Y_classes = self.classes[np.argmax(Y_softmax, axis=1)]
            return Y_classes, Y_softmax
        else:
            return Y

    def _bprop(self, X, Y, learning_rate, target=None):
        if self.classifier:
            delta = -2 * (self.iv - Y)    
        else:
            delta = -2 * (target - Y)
            
        for i in range(len(self.weights)-1, 0, -1):
            self.weights[i] -= learning_rate * self._add_ones(self.Hs[i]).T @ delta
            delta = delta @ self.weights[i][1:, :].T * self._df(self.Hs[i])

        self.weights[0] -= learning_rate * self._add_ones(X).T @ delta

    def _standardizeX(self, X):        
        if self.X_means is None:
            self.X_means = np.mean(X, axis=0)
            self.X_stds = np.std(X, axis=0)
            self.X_stds[self.X_stds == 0] = 1
        return (X - self.X_means) / self.X_stds
        
    def _standardizeT(self, T):
        # return T
        if self.T_means is None:
            self.T_means = np.mean(T, axis=0)
            self.T_stds = np.std(T, axis=0)
            self.T_stds[self.T_stds == 0] = 1
        return (T - self.T_means) / self.T_stds

    def _unstandardizeT(self, T):
        # return T
        
        if self.T_means is None:
            raise Exception('T not standardized yet')

        return (T * self.T_stds) + self.T_means
    
    def _E(self, X, T_iv_or_T):
        if self.classifier:
            Y_class_names, Y_softmax = self.use(X, standardized=True)
            sq_diffs = (T_iv_or_T - Y_softmax) ** 2
        else:
            Y = self.use(X, standardized=True)
            sq_diffs = (T_iv_or_T - Y) ** 2
        return np.mean(sq_diffs)
    
    def _add_ones(self, M):
        return np.insert(M, 0, 1, 1)

    def _make_indicator_vars(self, T):
        return (T == np.unique(T)).astype(int)

    def _softmax(self, Y):
        fs = np.exp(Y)  # N x K
        denom = np.sum(fs, axis=1).reshape((-1, 1))
        return fs / denom

    def _f(self, S):
        return np.tanh(S)

    def _df(self, fS):
        return (1 - fS ** 2)

    def percent_correct(self, T, Y_classes):
        return 100 * np.mean(T == Y_classes)

    def plot_mse_trace(self):
        if len(self.mse_trace) == 0:
            print("Train Model Before Attempting to Plot!")
            return None

        plt.plot(self.mse_trace)
        plt.title("MSE Trace")
        plt.xlabel("Epoch #")
        plt.ylabel("MSE")

    def plot_percent_correct_trace(self):
        if len(self.percent_correct_trace) == 0:
            print("Train Model Before Attempting to Plot!")
            return None

        plt.plot(self.percent_correct_trace)
        plt.title("% Correct Trace")
        plt.xlabel("Epoch #")
        plt.ylabel("% Correct")



    def plot_clusters(self, T):
        index = 0

        for i, H in enumerate(self.Hs):
            if H.shape[1] == 2:
                index = i
                break



        scatter = plt.scatter(self.Hs[index][:,0], self.Hs[index][:,1], c=T[:,0])
        plt.legend(handles=scatter.legend_elements()[0], 
           title="feed", labels=self.target_dict.keys());
        return scatter
    