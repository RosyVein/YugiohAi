import gym
import numpy as np
from gym import spaces


class YugiohEnv(gym.Env):
    def __init__(self) -> None:
        super(YugiohEnv, self).__init__()
