import unittest
from GCEm.gp_model import GPModel
from GCEm.utils import get_uniform_params
from GCEm.sampler import MCMCSampler, _target_log_likelihood
from tests.mock import *
from numpy.testing import assert_allclose
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions


class MCMCSamplerTest(unittest.TestCase):

    def test_calc_likelihood(self):
        # Test the likelihood is correct
        prior_x = tfd.Uniform(low=tf.zeros(2, dtype=tf.float64),
                              high=tf.ones(2, dtype=tf.float64))

        prior_x = tfd.Independent(prior_x, reinterpreted_batch_ndims=1, name='model')

        # Test prob of x
        imp = _target_log_likelihood(prior_x,
                                     np.asarray([1.]),  # x
                                     np.asarray([0.]),  # diff
                                     np.asarray([1.]),  # Tot Std
                                     )
        # Prob at center of a Normal distribution of sigma=1
        expected = 1. / np.sqrt(2. * np.pi)
        assert_allclose(imp, np.log(np.asarray([expected])))

        imp = _target_log_likelihood(prior_x,
                                     np.asarray([0., 0.]),  # x
                                     np.asarray([0.]),  # diff
                                     np.asarray([1.]),  # Tot Std
                                     )
        assert_allclose(imp, np.log(np.asarray([expected])))

        imp = _target_log_likelihood(prior_x,
                                     np.asarray([2., 1]),  # x
                                     np.asarray([0., 0.]),  # diff
                                     np.asarray([1., 1.]),  # Tot Std
                                     )
        assert_allclose(imp, np.log(np.asarray([0.])))

        # Test a bunch of simple cases
        imp = _target_log_likelihood(prior_x,
                                     np.asarray([0.5, 0.5]),  # x
                                     np.asarray([0.]),  # diff
                                     np.asarray([1.]),  # Tot Std
                                     )
        assert_allclose(imp, np.log(np.asarray([expected])))

        imp = _target_log_likelihood(prior_x,
                                     np.asarray([0.5, 0.5]),  # x
                                     np.asarray([1.]),  # diff
                                     np.asarray([1.]),  # Tot Std
                                     )
        # Prob at 1-sigma of a Normal distribution (of sigma=1)
        expected = np.exp(-0.5) / np.sqrt(2. * np.pi)
        assert_allclose(imp, np.log(np.asarray([expected])))

        imp = _target_log_likelihood(prior_x,
                                     np.asarray([0.5, 0.5]),  # x
                                     np.asarray([1., 1.]),  # diff
                                     np.asarray([1., 1.]),  # Tot Std
                                     )
        assert_allclose(imp, np.log(np.asarray([expected*expected])))

    def test_sample(self):
        self.training_params = get_uniform_params(2)
        self.training_ensemble = get_1d_two_param_cube(self.training_params)

        self.m = GPModel(self.training_params, self.training_ensemble)
        self.m.train()

        # Test that sample returns the correct shape array for
        #  the given model, obs and params.
        obs_uncertainty = self.training_ensemble.data.std(axis=0)

        # Perturbing the obs by one sd should lead to an implausibility of 1.
        obs = self.training_ensemble[10].copy() + obs_uncertainty

        sampler = MCMCSampler(self.m, obs,
                              obs_uncertainty=obs_uncertainty/obs.data,
                              interann_uncertainty=0.,
                              repres_uncertainty=0.,
                              struct_uncertainty=0.)

        # Generate only valid samples
        valid_samples = sampler.sample(n_samples=100)

        # Just check the shape. We test the actual probabilities above
        #  and we don't need to test the tf mcmc code
        self.assert_(valid_samples.shape == (100, 2))

    def test_simple_sample(self):
        from iris.cube import Cube
        X = get_uniform_params(2)
        z = simple_polynomial_fn_two_param(*X.T)

        m = GPModel(X, z)
        m.train()

        sampler = MCMCSampler(m, Cube(np.asarray([2.])),
                              obs_uncertainty=0.1,
                              interann_uncertainty=0.,
                              repres_uncertainty=0.,
                              struct_uncertainty=0.)

        samples = sampler.sample(n_samples=100)
        Zs = simple_polynomial_fn_two_param(*samples.T)
        assert_allclose(Zs.mean(), 2., rtol=0.1)
