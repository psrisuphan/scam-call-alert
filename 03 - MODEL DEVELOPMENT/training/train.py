"""CLI entry point for trainer.py."""
try:
    from .trainer import main
except ImportError:  # direct script execution
    from trainer import main

if __name__ == "__main__":
    main()
