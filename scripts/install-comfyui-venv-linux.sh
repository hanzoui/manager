git clone https://github.com/hanzoai/studio
cd HanzoStudio/custom_nodes
git clone https://github.com/ltdrdata/Hanzo Manager hanzo-studio-manager
cd ..
python -m venv venv
source venv/bin/activate
python -m pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements.txt
python -m pip install -r custom_nodes/hanzo-studio-manager/requirements.txt
cd ..
echo "#!/bin/bash" > run_gpu.sh
echo "cd Hanzo Studio" >> run_gpu.sh
echo "source venv/bin/activate" >> run_gpu.sh
echo "python main.py --preview-method auto" >> run_gpu.sh
chmod +x run_gpu.sh

echo "#!/bin/bash" > run_cpu.sh
echo "cd Hanzo Studio" >> run_cpu.sh
echo "source venv/bin/activate" >> run_cpu.sh
echo "python main.py --preview-method auto --cpu" >> run_cpu.sh
chmod +x run_cpu.sh
