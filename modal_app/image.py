"""Modal image for Chronos inference and stock prediction (torch, chronos, alpaca-py, etc.)."""

import modal

chronos_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.0.0",
        "chronos-forecasting>=2.2.2",
        "alpaca-py>=0.15.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.0.0",
        "hmmlearn>=0.2.7",
        "textblob>=0.17.1",
        "arch>=6.0.0",
        "plotly>=5.0.0",
        "pytz>=2023.3",
    )
)
