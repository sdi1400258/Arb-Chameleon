"""
Simplified PPO training script without strict environment checking
"""
from stable_baselines3 import PPO
from arb_env import ArbitrageEnv
import os


def train_simple(timesteps=50000):
    """Train PPO agent without strict env checking"""
    print("Creating environment...")
    env = ArbitrageEnv(simulation_mode=True)
    
    print("Creating PPO model...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        verbose=1
    )
    
    print(f"\nStarting training for {timesteps} timesteps...")
    model.learn(total_timesteps=timesteps)
    
    # Save model
    os.makedirs("../models", exist_ok=True)
    model_path = "../models/ppo_arb_simple"
    model.save(model_path)
    print(f"\n Training complete! Model saved to {model_path}")
    
    return model


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=50000)
    args = parser.parse_args()
    
    train_simple(args.timesteps)
