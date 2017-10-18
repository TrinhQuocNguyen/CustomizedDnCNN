'''
DnCNN
paper: Beyond a Gaussian Denoiser: Residual Learning of Deep CNN for Image Denoising

a tensorflow version of the network DnCNN
just for personal exercise

author: momogary
'''

import tensorflow as tf
import numpy as np
import math, os
from glob import glob
from ops import *
from utils import *
from six.moves import xrange
import time
from guidedfilter import guidedfilter


class DnCNN(object):
	def __init__(self, sess, image_size=40, batch_size=128,
					output_size=40, input_c_dim=1, output_c_dim=1,
					sigma=25, clip_b=0.025, lr=0.01, epoch=50,
					ckpt_dir='./checkpoint', sample_dir='./sample',
					test_save_dir='./test',
					dataset='BSD400', testset='Set12'):
		self.sess = sess
		self.is_gray = (input_c_dim == 1)
		self.batch_size = batch_size
		self.image_size = image_size
		self.output_size = output_size
		self.input_c_dim = input_c_dim
		self.output_c_dim = output_c_dim
		self.sigma = sigma
		self.clip_b = clip_b
		self.lr = lr
		self.numEpoch = epoch
		self.ckpt_dir = ckpt_dir
		self.trainset = dataset
		self.testset = testset
		self.sample_dir = sample_dir
		self.test_save_dir = test_save_dir
		self.epoch = epoch
		self.save_every_iter = 1862
		self.eval_every_iter = 1862
		# Adam setting (default setting)
		self.beta1 = 0.9
		self.beta2 = 0.999
		self.alpha = 0.01
		self.epsilon = 1e-8

		self.build_model()


	def build_model(self):
		#input : [batchsize, image_size, image_size, channel]
		self.X = tf.placeholder(tf.float32, \
					[None, self.image_size, self.image_size, self.input_c_dim], \
					name='noisy_image')
		self.X_ = tf.placeholder(tf.float32, \
					[None, self.image_size, self.image_size, self.input_c_dim], \
					name='clean_image')
		# self.X = tf.placeholder(tf.float32, \
		# 			[self.image_size, self.image_size, self.input_c_dim,None], \
		# 			name='noisy_image')
		# self.X_ = tf.placeholder(tf.float32, \
		# 			[self.image_size, self.image_size, self.input_c_dim,None], \
		# 			name='clean_image')

		# layer 1
		with tf.variable_scope('conv1'):
			layer_1_output = self.layer(self.X, [3, 3, self.input_c_dim, 64], useBN=False)

		# layer 2 to 16
		with tf.variable_scope('conv2'):
			layer_2_output = self.layer(layer_1_output, [3, 3, 64, 64])
		with tf.variable_scope('conv3'):
			layer_3_output = self.layer(layer_2_output, [3, 3, 64, 64])
		with tf.variable_scope('conv4'):
			layer_4_output = self.layer(layer_3_output, [3, 3, 64, 64])
		with tf.variable_scope('conv5'):
			layer_5_output = self.layer(layer_4_output, [3, 3, 64, 64])
		with tf.variable_scope('conv6'):
			layer_6_output = self.layer(layer_5_output, [3, 3, 64, 64])
		with tf.variable_scope('conv7'):
			layer_7_output = self.layer(layer_6_output, [3, 3, 64, 64])
		with tf.variable_scope('conv8'):
			layer_8_output = self.layer(layer_7_output, [3, 3, 64, 64])
		with tf.variable_scope('conv9'):
			layer_9_output = self.layer(layer_8_output, [3, 3, 64, 64])
		with tf.variable_scope('conv10'):
			layer_10_output = self.layer(layer_9_output, [3, 3, 64, 64])
		with tf.variable_scope('conv11'):
			layer_11_output = self.layer(layer_10_output, [3, 3, 64, 64])
		with tf.variable_scope('conv12'):
			layer_12_output = self.layer(layer_11_output, [3, 3, 64, 64])
		with tf.variable_scope('conv13'):
			layer_13_output = self.layer(layer_12_output, [3, 3, 64, 64])
		with tf.variable_scope('conv14'):
			layer_14_output = self.layer(layer_13_output, [3, 3, 64, 64])
		with tf.variable_scope('conv15'):
			layer_15_output = self.layer(layer_14_output, [3, 3, 64, 64])
		with tf.variable_scope('conv16'):
			layer_16_output = self.layer(layer_15_output, [3, 3, 64, 64])

		# layer 17
		with tf.variable_scope('conv17'):
			self.Y = self.layer(layer_16_output, [3, 3, 64, self.output_c_dim], useBN=False)
			# # self.Y_ = self.X - self.Y
			# for index in xrange(0,128):
			# 	self.Y_[index,:,:,:] = guidedfilter(self.Y[index,:,:,:],self.X[index,:,:,:],5,0.0004)

		# L2 loss
		self.Y_ = self.X - self.X_ # noisy image - clean image
		self.loss = (1.0 / self.batch_size) * tf.nn.l2_loss(self.Y_ - self.Y)

		optimizer = tf.train.AdamOptimizer(self.lr, name='AdamOptimizer')
		self.train_step = optimizer.minimize(self.loss)
		# create this init op after all variables specified
		self.init = tf.global_variables_initializer()
		self.saver = tf.train.Saver()
		print("[*] Initialize model successfully...")

	def conv_layer(self, inputdata, weightshape, b_init, stridemode):
		# weights
		W = tf.get_variable('weights', weightshape, initializer = \
							tf.constant_initializer(get_conv_weights(weightshape, self.sess)))
		b = tf.get_variable('biases', [1, weightshape[-1]], initializer = \
							tf.constant_initializer(b_init))

		# convolutional layer
		return tf.nn.conv2d(inputdata, W, strides=stridemode, padding="SAME") + b # SAME with zero padding

	def bn_layer(self, logits, output_dim, b_init = 0.0):
		alpha = tf.get_variable('bn_alpha', [1, output_dim], initializer = \
								tf.constant_initializer(get_bn_weights([1, output_dim], self.clip_b, self.sess)))
		beta = tf.get_variable('bn_beta', [1, output_dim], initializer = \
								tf.constant_initializer(b_init))
		return batch_normalization(logits, alpha, beta, isCovNet = True)

	def layer(self, inputdata, filter_shape, b_init = 0.0, stridemode=[1,1,1,1], useBN = True):
		logits = self.conv_layer(inputdata, filter_shape, b_init, stridemode)
		if useBN:
			output = tf.nn.relu(self.bn_layer(logits, filter_shape[-1]))
		else:
			output = tf.nn.relu(logits)
		return output

	def train(self):
		# init the variables
		self.sess.run(self.init)

		# get data
		test_files = glob('./data/test/{}/*.png'.format(self.testset))
		test_data = load_images(test_files) # list of array of different size, 4-D
		data = load_data(filepath='./data/img_clean_pats.npy')
		numBatch = int(data.shape[0] / self.batch_size)
		print("[*] Data shape = " + str(data.shape))

		counter = 0
		print("[*] Start training : ")
		start_time = time.time()
		for epoch in range(self.epoch):
			for batch_id in range(numBatch):
				batch_images = data[batch_id*self.batch_size:(batch_id+1)*self.batch_size,:, :, :]
				# print(str(batch_images.shape))

				train_images = add_noise(batch_images, self.sigma, self.sess)

				# print(str(train_images.shape))
				_, loss = self.sess.run([self.train_step, self.loss], \
						feed_dict={self.X:train_images, self.X_:batch_images})
				print(epoch + 1, batch_id + 1, numBatch,
						time.time() - start_time, loss)

				counter += 1

				if np.mod(counter, self.eval_every_iter) == 0:
					self.evaluate(epoch, counter, test_data)
				# save the model
				if np.mod(counter, self.save_every_iter) == 0:
					self.save(counter)
		print("[*] Finish training.")

	def save(self,counter):
		model_name = "DnCNN.model"
		model_dir = "%s_%s_%s" % (self.trainset, \
									self.batch_size, self.image_size)
		checkpoint_dir = os.path.join(self.ckpt_dir, model_dir)

		if not os.path.exists(checkpoint_dir):
			os.makedirs(checkpoint_dir)

		print("[*] Saving model...")
		self.saver.save(self.sess,
						os.path.join(checkpoint_dir, model_name),
						global_step=counter)

	def sampler(self, image):
		# set reuse flag to True
		#tf.get_variable_scope().reuse_variables()

		self.X_test = tf.placeholder(tf.float32, \
					image.shape, name='noisy_image_test')

		# layer 1 (adpat to the input image)
		with tf.variable_scope('conv1', reuse=True):
			layer_1_output = self.layer(self.X_test, [3, 3, self.input_c_dim, 64], useBN=False)

		# layer 2 to 16
		with tf.variable_scope('conv2', reuse=True):
			layer_2_output = self.layer(layer_1_output, [3, 3, 64, 64])
		with tf.variable_scope('conv3', reuse=True):
			layer_3_output = self.layer(layer_2_output, [3, 3, 64, 64])
		with tf.variable_scope('conv4', reuse=True):
			layer_4_output = self.layer(layer_3_output, [3, 3, 64, 64])
		with tf.variable_scope('conv5', reuse=True):
			layer_5_output = self.layer(layer_4_output, [3, 3, 64, 64])
		with tf.variable_scope('conv6', reuse=True):
			layer_6_output = self.layer(layer_5_output, [3, 3, 64, 64])
		with tf.variable_scope('conv7', reuse=True):
			layer_7_output = self.layer(layer_6_output, [3, 3, 64, 64])
		with tf.variable_scope('conv8', reuse=True):
			layer_8_output = self.layer(layer_7_output, [3, 3, 64, 64])
		with tf.variable_scope('conv9', reuse=True):
			layer_9_output = self.layer(layer_8_output, [3, 3, 64, 64])
		with tf.variable_scope('conv10', reuse=True):
			layer_10_output = self.layer(layer_9_output, [3, 3, 64, 64])
		with tf.variable_scope('conv11', reuse=True):
			layer_11_output = self.layer(layer_10_output, [3, 3, 64, 64])
		with tf.variable_scope('conv12', reuse=True):
			layer_12_output = self.layer(layer_11_output, [3, 3, 64, 64])
		with tf.variable_scope('conv13', reuse=True):
			layer_13_output = self.layer(layer_12_output, [3, 3, 64, 64])
		with tf.variable_scope('conv14', reuse=True):
			layer_14_output = self.layer(layer_13_output, [3, 3, 64, 64])
		with tf.variable_scope('conv15', reuse=True):
			layer_15_output = self.layer(layer_14_output, [3, 3, 64, 64])
		with tf.variable_scope('conv16', reuse=True):
			layer_16_output = self.layer(layer_15_output, [3, 3, 64, 64])

		# layer 17
		with tf.variable_scope('conv17', reuse=True):
			self.Y_test = self.layer(layer_16_output, [3, 3, 64, self.output_c_dim], useBN=False)

	def load(self, checkpoint_dir):
		'''Load checkpoint file'''
		print("[*] Reading checkpoint...")

		model_dir = "%s_%s_%s" % (self.trainset, self.batch_size, self.image_size)
		checkpoint_dir = os.path.join(checkpoint_dir, model_dir)

		ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
		if ckpt and ckpt.model_checkpoint_path:
			ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
			self.saver.restore(self.sess, os.path.join(checkpoint_dir, ckpt_name))
			return True
		else:
			return False

	def forward(self, noisy_image):
		'''forward once'''
		self.sampler(noisy_image)
		return self.sess.run(self.Y_test, feed_dict={self.X_test:noisy_image})

	def test(self):
		"""Test DnCNN"""
		# init variables
		tf.initialize_all_variables().run()

		test_files = glob(os.path.join(self.test_save_dir, '{}/*.png'.format(self.testset)))

		# load testing input
		print("[*] Loading test images ...")
		test_data = load_images(test_files) # list of array of different size

		if self.load(self.ckpt_dir):
			print(" [*] Load SUCCESS")
		else:
			print(" [!] Load failed...")

		psnr_sum = 0
		for idx in range(len(test_files)):
			noisy_image = add_noise(1 / 255.0 * test_data[idx], self.sigma, self.sess)  # ndarray
			predicted_noise = self.forward(noisy_image)
			output_clean_image = (noisy_image - predicted_noise) * 255
 			# calculate PSNR
			psnr = cal_psnr(test_data[idx], output_clean_image)
			psnr_sum += psnr
			save_images(test_data[idx], noisy_image * 255, output_clean_image, \
						os.path.join(self.test_save_dir, '%s/test%d_%d_%d.png' % (self.testset, idx, epoch, counter)))
		avg_psnr = psnr_sum / len(test_files)
		print("--- Average PSNR %.2f ---" % avg_psnr)

	def evaluate(self, epoch, counter, test_data):
		'''Evaluate the model during training'''

		#print("[*] Evaluating...")
		psnr_sum = 0
		# for idx in xrange(len(test_files)):
		for idx in range(len(test_data)):

			noisy_image = add_noise(1 / 255.0 * test_data[idx], self.sigma, self.sess)  # ndarray
			predicted_noise = self.forward(noisy_image)
			output_clean_image = (noisy_image - predicted_noise) * 255

			groundtruth = np.clip(255 * test_data[idx], 0, 255).astype('uint8')
			noisyimage = np.clip(noisy_image * 255, 0, 255).astype('uint8')
			outputimage = np.clip(output_clean_image, 0, 255).astype('uint8')

 			# calculate PSNR
			psnr = cal_psnr(groundtruth, outputimage)
			psnr_sum += psnr
			save_images(groundtruth, noisyimage, outputimage, \
						os.path.join(self.sample_dir, 'test%d_%d_%d.png' % (idx, epoch, counter)))
		avg_psnr = psnr_sum / len(test_data)
		print("--- Test ---- Average PSNR %.2f ---" % avg_psnr)




