.\python_embeded\python.exe -s -m pip install gitpython
.\python_embeded\python.exe -c "import git; git.Repo.clone_from('https://github.com/ltdrdata/Hanzo Manager', './HanzoStudio/custom_nodes/hanzo-studio-manager')"
.\python_embeded\python.exe -m pip install -r ./HanzoStudio/custom_nodes/hanzo-studio-manager/requirements.txt
