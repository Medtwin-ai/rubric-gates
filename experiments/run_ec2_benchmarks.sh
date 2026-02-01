#!/bin/bash
# PATH: experiments/run_ec2_benchmarks.sh
# PURPOSE: Run benchmark experiments on EC2 with clinical datasets
#
# USAGE:
#   ./run_ec2_benchmarks.sh [--quick|--full]
#
# OPTIONS:
#   --quick  Run with reduced dataset (10 artifacts per task)
#   --full   Run full benchmark (100 artifacts per task)

set -e

# Configuration
EC2_HOST="16.176.51.96"
EC2_USER="ubuntu"
SSH_KEY="$HOME/.ssh/clinical-data-key.pem"
DATA_ROOT="/opt/clinical_data"
WORK_DIR="/opt/clinical_data/rubric-gates-experiments"

# Parse arguments
MODE="quick"
N_ARTIFACTS=10
if [[ "$1" == "--full" ]]; then
    MODE="full"
    N_ARTIFACTS=100
fi

echo "=================================================="
echo "Rubric Gates Benchmark Runner"
echo "=================================================="
echo "Mode: $MODE"
echo "Artifacts per task: $N_ARTIFACTS"
echo "EC2: $EC2_USER@$EC2_HOST"
echo ""

# Check SSH key
if [[ ! -f "$SSH_KEY" ]]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    exit 1
fi

# Test connection
echo "[1/5] Testing EC2 connection..."
ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo 'Connected!'" || {
    echo "ERROR: Cannot connect to EC2"
    exit 1
}

# Setup experiment directory on EC2
echo "[2/5] Setting up experiment environment on EC2..."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'SETUP_EOF'
set -e

# Create work directory
mkdir -p /opt/clinical_data/rubric-gates-experiments
cd /opt/clinical_data/rubric-gates-experiments

# Install Python packages if needed
if ! python3 -c "import duckdb" 2>/dev/null; then
    echo "Installing Python packages..."
    pip3 install --user duckdb pandas numpy
fi

# Clone/update rubric-gates if needed
if [[ ! -d "rubric-gates" ]]; then
    git clone https://github.com/Medtwin-ai/rubric-gates.git
else
    cd rubric-gates && git pull && cd ..
fi

echo "Setup complete"
SETUP_EOF

# Copy latest experiment files
echo "[3/5] Syncing experiment files..."
rsync -avz -e "ssh -i $SSH_KEY" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='*.pyc' \
    "$(dirname "$0")/../" \
    "$EC2_USER@$EC2_HOST:$WORK_DIR/rubric-gates/"

# Run experiments
echo "[4/5] Running experiments (this may take a while)..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << EXPERIMENT_EOF
set -e
cd $WORK_DIR/rubric-gates

# Set data paths
export MIMIC_IV_PATH="$DATA_ROOT/mimic-iv-full/2.2"
export EICU_PATH="$DATA_ROOT/eicu-crd-full/2.0"

# Run benchmark
python3 experiments/run_benchmarks.py \
    --datasets mimic_iv eicu \
    --baselines B0 B1 B2 B3 B4 \
    --n-artifacts $N_ARTIFACTS \
    --output ./results/${TIMESTAMP}

echo ""
echo "Results saved to: ./results/${TIMESTAMP}"
ls -la ./results/${TIMESTAMP}/
EXPERIMENT_EOF

# Download results
echo "[5/5] Downloading results..."
RESULTS_DIR="./results/${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"
scp -i "$SSH_KEY" -r \
    "$EC2_USER@$EC2_HOST:$WORK_DIR/rubric-gates/results/${TIMESTAMP}/*" \
    "$RESULTS_DIR/"

echo ""
echo "=================================================="
echo "Benchmark Complete!"
echo "=================================================="
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Next steps:"
echo "  1. Review results: cat $RESULTS_DIR/summary_*.md"
echo "  2. Generate figures: python experiments/generate_figures.py --results $RESULTS_DIR/results_*.json"
echo ""
