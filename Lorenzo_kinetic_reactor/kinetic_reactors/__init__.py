"""
===================================
Reactor kinetics Package
===================================
"""

from ._kineticReactionSystem import KineticExpression, ReactionModel
from ._reactorBATCH import KineticBATCH
from ._reactorCSTR import KineticCSTR
from ._reactorPFR import KineticPFR

__version__ = "1.0.0"
__author__ = "David Lorenzo"

print(f"🚀 Kinetic Reactors Package v{__version__} loaded")