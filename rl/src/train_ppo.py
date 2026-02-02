"""
PPO Training script for the arbitrage RL agent
"""
import sys
sys.path.append('..')
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from arb_env import ArbitrageEnv
import os


def train_ppo_agent(
    total_timesteps: int = 1_000_000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    save_path: str = "../models"
):
    """
    Train a PPO agent for arbitrage strategy optimization
    
    Args:
        total_timesteps: Total training timesteps
        learning_rate: Learning rate for PPO
        n_steps: Number of steps to run for each environment per update
        batch_size: Minibatch size
        save_path: Directory to save models
    """
    # Create environment
    env = ArbitrageEnv(simulation_mode=True)
    
    # Validate environment
    print("Checking environment...")
    check_env(env, warn=True)
    print("Environment check passed!")
    
    # Create eval environment
    eval_env = ArbitrageEnv(simulation_mode=True)
    
    # Create callbacks
    os.makedirs(save_path, exist_ok=True)
    os.makedirs(f"{save_path}/checkpoints", exist_ok=True)
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=save_path,
        log_path=f"{save_path}/logs",
        eval_freq=10000,
        deterministic=True,
        render=False
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=f"{save_path}/checkpoints",
        name_prefix="ppo_arb"
    )
    
    # Create PPO model
    print("Creating PPO model...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        tensorboard_log=f"{save_path}/tensorboard"
    )
    
    # Train the model
    print(f"Starting training for {total_timesteps} timesteps...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True
    )
    
    # Save final model
    final_path = f"{save_path}/ppo_arb_final"
    model.save(final_path)
    print(f"Training complete! Model saved to {final_path}")
    
    return model


def test_trained_agent(model_path: str, num_episodes: int = 10):
    """
    Test a trained agent
    
    Args:
        model_path: Path to the trained model
        num_episodes: Number of episodes to test
    """
    env = ArbitrageEnv(simulation_mode=True)
    model = PPO.load(model_path)
    
    total_rewards = []
    total_pnls = []
    
    for episode in range(num_episodes):
        obs, info = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated
        
        total_rewards.append(episode_reward)
        total_pnls.append(info['total_pnl'])
        
        print(f"Episode {episode + 1}: Reward = {episode_reward:.2f}, "
              f"PnL = ${info['total_pnl']:.2f}, "
              f"Successes = {info['num_successes']}, "
              f"Reverts = {info['num_reverts']}")
    
    print(f"\nAverage Reward: {sum(total_rewards) / len(total_rewards):.2f}")
    print(f"Average PnL: ${sum(total_pnls) / len(total_pnls):.2f}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train or test PPO agent for arbitrage")
    parser.add_argument("--mode", choices=["train", "test"], default="train",
                        help="Mode: train or test")
    parser.add_argument("--timesteps", type=int, default=100000,
                        help="Total training timesteps")
    parser.add_argument("--model-path", type=str, default="../models/ppo_arb_final",
                        help="Path to model (for testing)")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        train_ppo_agent(total_timesteps=args.timesteps)
    else:
        test_trained_agent(args.model_path)
