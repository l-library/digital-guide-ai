source ~/software/anaconda3/etc/profile.d/conda.sh
conda activate DGA
export LLM_API_KEY=sk-65d54b40f8a0480c86dedb316ce13304
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL_NAME=deepseek-v4-flash

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
