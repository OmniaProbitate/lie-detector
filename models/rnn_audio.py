
# Python Imports
import argparse

# Torch Imports
import torch
#from torch import LongTensor
#from torchtext.vocab import load_word_vectors
from torch.autograd import Variable
#from torch.nn.utils.rnn import pack_padded_sequence#, pad_packed_sequence
import torch.optim as optim
from torch.utils.data import DataLoader 
from torch import cuda, FloatTensor
from torch import nn
from torch.utils.data.sampler import SubsetRandomSampler

# Our modules
from models import *
from utils import *

############
## CONFIG ##
############

class Config:
  def __init__(self, args):
    self.epochs = args.e
    self.batch_size = args.bs
    self.lr = args.lr
    self.nt = args.nt
    self.nv = args.nv
    self.print_every = args.pe
    self.hidden_size = args.hs
    self.feats = args.feats
    self.labels = args.labels
    self.max_length = args.length
    #self.eval_every = args.ee
    self.use_gpu = args.gpu
    self.dtype = cuda.FloatTensor if self.use_gpu else FloatTensor
    self.num_classes = 2

  def __str__(self):
    properties = vars(self)
    properties = ["{} : {}".format(k, str(v)) for k, v in properties.items()]
    properties = '\n'.join(properties)
    properties = "--- Config --- \n" + properties + "\n"
    return properties

def parseConfig(description="Default Model Description"):
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('--feats', type=str, help='input features path', default = "../data/features/extracted_features_0.1_0.05.json")
  parser.add_argument('--labels', type=str, help='input labels', default = "../data/features/labels_0.1_0.05.json")
  parser.add_argument('--length', type=int, help='length of sequence', default = 300)
  parser.add_argument('--bs', type=int, help='batch size for training', default = 20)
  parser.add_argument('--e', type=int, help='number of epochs', default = 10)
  parser.add_argument('--nt', type=int, help='number of training examples', default = 100)
  parser.add_argument('--nv', type=int, help='number of validation examples', default = None)
  parser.add_argument('--hs', type=int, help='hidden size', default = 100)
  parser.add_argument('--lr', type=float, help='learning rate', default = 1e-3)
  parser.add_argument('--gpu', action='store_true', help='use gpu', default = False)
  parser.add_argument('--pe', type=int, help='print frequency', default = None)
  parser.add_argument('--ee', type=int, help='eval frequency', default = None)
  args = parser.parse_args()
  return args

############
# TRAINING #
############

def train(model, loss_fn, optimizer, num_epochs = 1):
  for epoch in range(num_epochs):
      print('Starting epoch %d / %d' % (epoch + 1, num_epochs))
      model.train()
      loss_total = 0
      for t, (x, y) in enumerate(model.config.train_loader):
          x_var = Variable(x)
          y_var = Variable(y.type(model.config.dtype).long())
          scores = model(x_var) 
          loss = loss_fn(scores, y_var)
          
          loss_total += loss.data[0]
          optimizer.zero_grad()
          loss.backward()

          optimizer.step()

          if ((t+1) % 10) == 0:
            grad_magnitude = [(x.grad.data.sum(), torch.numel(x.grad.data)) for x in model.parameters() if x.grad.data.sum() != 0.0]
            grad_magnitude = sum([abs(x[0]) for x in grad_magnitude]) #/ sum([x[1] for x in grad_magnitude])
            print('t = %d, avg_loss = %.4f, grad_mag = %.2f' % (t + 1, loss_total / (t+1), grad_magnitude))
          
          
      print("--- Evaluating ---")
      check_accuracy(model, model.config.train_loader, type = "train")
      check_accuracy(model, model.config.val_loader, type = "val")
      print("\n")
  print("\n--- Final Evaluation ---")
  check_accuracy(model, model.config.train_loader, type = "train")
  check_accuracy(model, model.config.val_loader, type = "val")
  #check_accuracy(model, model.config.test_loader, type = "test")


def check_accuracy(model, loader, type=""):
  print("Checking accuracy on {} set".format(type))
  num_correct = 0
  num_samples = 0
  model.eval() # Put the model in test mode (the opposite of model.train(), essentially)
  for t, (x, y) in enumerate(loader):
      x_var = Variable(x)
      #y_var = Variable(y.type(model.config.dtype).long())
      scores = model(x_var)
      _, preds = scores.data.cpu().max(1)
      num_correct += (preds == y).sum()
      num_samples += preds.size(0)
      #print("Completed evaluating {} examples".format(t*model.config.batch_size))
  acc = float(num_correct) / num_samples
  print('Got %d / %d correct (%.2f)' % (num_correct, num_samples, 100 * acc))


########
# MAIN #
########

def main():
  # Config
  args = parseConfig()
  config = Config(args) 
  print(config)

  # Load Embeddings
  #vocab, embeddings, embedding_dim = load_word_vectors('.', 'glove.6B', 100)

  # Model
  model = ComplexAudioRNN_1(config)
  model.apply(initialize_weights)
  if config.use_gpu:
    model = model.cuda()


  # Load Data
  train_dataset = AudioDataset(config)

  train_idx, val_idx = splitIndices(train_dataset, config, shuffle = True)
  train_sampler, val_sampler = SubsetRandomSampler(train_idx), SubsetRandomSampler(val_idx)
  train_loader = DataLoader(train_dataset, batch_size = config.batch_size, num_workers = 3, sampler = train_sampler)
  val_loader = DataLoader(train_dataset, batch_size = config.batch_size, num_workers = 1, sampler = val_sampler)

  train_dataset.printDistributions(train_idx, msg = "Training")
  train_dataset.printDistributions(val_idx, msg = "Val")

  config.train_loader = train_loader
  config.val_loader = val_loader

  optimizer = optim.Adam(model.parameters(), lr = config.lr) 
  loss_fn = nn.CrossEntropyLoss().type(config.dtype)
  train(model, loss_fn, optimizer, config.epochs)
  

if __name__ == '__main__':
  main()