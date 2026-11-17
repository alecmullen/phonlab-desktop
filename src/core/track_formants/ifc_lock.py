import threading

# phonlab's numba-accelerated IFC code runs its frames on all cores, and numba's
# default threading layer may abort if two threads enter parallel code at once.
# Everything that calls IFC_formants (or its warm-up) holds this lock.
IFC_LOCK = threading.Lock()
