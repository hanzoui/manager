git clone https://github.com/hanzoai/studio
cd HanzoStudio/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager hanzo-studio-manager
cd ..
python -m venv venv
call venv/Scripts/activate
python -m pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements.txt
python -m pip install -r custom_nodes/hanzo-studio-manager/requirements.txt
cd ..
echo "cd Hanzo Studio" >> run_gpu.bat
echo "call venv/Scripts/activate" >> run_gpu.bat
echo "python main.py" >> run_gpu.bat

echo "cd Hanzo Studio" >> run_cpu.bat
echo "call venv/Scripts/activate" >> run_cpu.bat
echo "python main.py --cpu" >> run_cpu.bat
