# build_files.sh
echo "Building the project..."
python3.12 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt

echo "Collect Static..."
python manage.py collectstatic --noinput --clear
