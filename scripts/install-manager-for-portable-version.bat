.\python_embeded\python.exe -s -m pip install gitpython
.\python_embeded\python.exe -c "import git; git.Repo.clone_from('https://github.com/ltdrdata/Hanzo Manager', './Hanzo Studio/custom_nodes/hanzo-studio-manager')"
.\python_embeded\python.exe -m pip install -r ./Hanzo Studio/custom_nodes/hanzo-studio-manager/requirements.txt
