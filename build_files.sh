# build_files.sh
echo "Building the project..."
# pip install is handled by Vercel automatically


echo "Make Migration..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Collect Static..."
python manage.py collectstatic --noinput --clear
