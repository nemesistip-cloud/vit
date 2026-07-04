from app.core.kernel import kernel
try:
    print(f"Kernel has get_subsystem: {hasattr(kernel, 'get_subsystem')}")
except Exception as e:
    print(f"Error checking kernel: {e}")
