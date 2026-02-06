# build_files.sh
echo "Building the project..."
# pip install is handled by Vercel automatically

echo "Collect Static..."
python manage.py collectstatic --noinput --clear
