"""Adapter for the architecture-owned OR-Tools solver."""
from optimizer.model import solve, SolveOptions

class LiveOptimizer:
    def generate(self, world, objective, **kwargs):
        return solve(world, SolveOptions(profile=objective))

def optimizer_port():
    return LiveOptimizer()
