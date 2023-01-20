"""Tests whether the snn MDSA algorithm results equal those of the
default/Neumann implementation."""
# pylint: disable=R0801

from typeguard import typechecked

from tests.sparse.MDSA.test_snn_results import Test_mdsa_snn_results


class Test_mdsa_snn_results_with_adaptation(Test_mdsa_snn_results):
    """Tests whether the snn implementation of the MDSA algorithm with
    adaptation yields the same results as the default/Neumann implementation if
    its weights are identical."""

    # Initialize test object
    #
    def __init__(self, *args, **kwargs) -> None:  # type:ignore[no-untyped-def]
        super(Test_mdsa_snn_results, self).__init__(*args, **kwargs)
        # Generate default experiment config.
        self.create_exp_config()

    @typechecked
    def test_something(self) -> None:
        """Tests whether the SNN MDSA algorithm without adaptation yields the
        same results as the original Neumann version of the MDSA algorithm."""
        self.helper(self.mdsa_settings)
