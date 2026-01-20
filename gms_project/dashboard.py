def dashboard_callback(request):
    """
    Callback function for the dashboard.
    """
    from django.shortcuts import redirect
    from django.urls import reverse
    
    # Replace with appropriate dashboard logic
    # Untuk sekarang, langsung redirect ke halaman admin utama
    return redirect(reverse('admin:index'))