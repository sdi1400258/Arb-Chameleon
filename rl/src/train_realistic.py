"""
Robust PPO training script for long-running realistic simulations
"""
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from arb_env import ArbitrageEnv
import os
import argparse
import time


def train_realistic(timesteps=10_000_000, model_name="ppo_arb_realistic"):
    """
    Train PPO agent on realistic environment with checkpoints
    """
    print(f"\n{'='*50}")
    print(f"Starting Realistic Training Session")
    print(f"Target Timesteps: {timesteps:,}")
    print(f"Model Name: {model_name}")
    print(f"{'='*50}\n")
    
    # Create environment
    env = ArbitrageEnv(simulation_mode=True)
    env = Monitor(env)  # Wrap for logging
    
    # Create directories
    models_dir = f"../models/{model_name}"
    logs_dir = f"../logs/{model_name}"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Checkpoints every 100k steps
    checkpoint_callback = CheckpointCallback(
        save_freq=100_000,
        save_path=models_dir,
        name_prefix="ckpt"
    )
    
    # Create model
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=4096,        # Increased for stable long-term learning
        batch_size=128,      # Increased batch size
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,       # Higher entropy to encourage exploration
        verbose=1,
        tensorboard_log=logs_dir,
        device="cpu"         # Explicitly set CPU
    )
    
    start_time = time.time()
    
    try:
        model.learn(
            total_timesteps=timesteps,
            callback=checkpoint_callback,
            progress_bar=False  # Disabled for simple logging
        )
        
        # Save final model
        final_path = f"{models_dir}/final_model"
        model.save(final_path)
        print(f"\n Training complete! Model saved to {final_path}")
        
    except KeyboardInterrupt:
        print("\n Training interrupted by user!")
        save_path = f"{models_dir}/interrupted_model"
        model.save(save_path)
        print(f"Saved checkpoint to {save_path}")
        
    end_time = time.time()
    duration = end_time - start_time
    print(f"Total training time: {duration/3600:.2f} hours")
    
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=10_000_000)
    parser.add_argument("--name", type=str, default="ppo_arb_realistic")
    args = parser.parse_args()
    
    train_realistic(args.timesteps, args.name)
