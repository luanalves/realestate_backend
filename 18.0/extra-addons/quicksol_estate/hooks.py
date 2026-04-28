"""
Module hooks for quicksol_estate.
"""


def post_init_hook(env):
    """Called after module installation or upgrade.
    Sets seed proposal states to cover all 8 FSM states for UI journey testing.
    """
    env['real.estate.proposal']._set_seed_proposal_states()
