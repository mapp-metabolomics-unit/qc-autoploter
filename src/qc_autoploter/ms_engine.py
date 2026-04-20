import numpy as np
from pyteomics import mzml
from scipy.signal import find_peaks
from scipy.integrate import simpson

# Cache for spectral data to avoid re-reading files
_cache = {}

def clear_cache():
    """Clear the spectral data cache."""
    global _cache
    _cache.clear()

def load_spectra(file_path):
    """Load spectral data from mzML file and cache it."""
    if file_path in _cache:
        return _cache[file_path]
    
    spectra = []
    with mzml.MzML(file_path) as reader:
        for spec in reader:
            if spec['ms level'] != 1:
                continue
            spectra.append({
                'rt': spec['scanList']['scan'][0]['scan start time'],
                'mz': np.array(spec['m/z array']),
                'intensity': np.array(spec['intensity array'])
            })
    
    _cache[file_path] = spectra
    return spectra

# --- extraction TIC (Total Ion Current) ---
def extract_tic(file_path):
    spectra = load_spectra(file_path)
    rt, intensity = [], []
    
    for spec in spectra:
        rt.append(spec['rt'])
        intensity.append(spec['intensity'].sum())
    
    return np.array(rt), np.array(intensity)

# --- extraction Orbitrap (ppm) ---
def extract_eic(file_path, target_mz, ppm=10):
    spectra = load_spectra(file_path)
    rt, intensity = [], []
    tol = target_mz * ppm * 1e-6
    
    for spec in spectra:
        mzs = spec['mz']
        ints = spec['intensity']
        mask = (mzs > target_mz - tol) & (mzs < target_mz + tol)
        rt.append(spec['rt'])
        intensity.append(ints[mask].sum() if np.any(mask) else 0)
    
    return np.array(rt), np.array(intensity)


# --- peak picking robuste ---
def pick_peaks(rt, intensity):
    if len(intensity) < 5:
        return np.array([])

    peaks, props = find_peaks(
        intensity,
        prominence=max(intensity)*0.02 if max(intensity)>0 else 1,
        height=max(intensity)*0.05 if max(intensity)>0 else 1,
        distance=3
    )

    return peaks


# --- Helper: Find dynamic peak boundaries ---
def find_peak_boundaries(intensity, peak_idx, threshold_percent=5):
    """
    Find dynamic boundaries of a peak by detecting where intensity drops below threshold.
    
    Args:
        intensity: array of intensity values
        peak_idx: index of the peak center
        threshold_percent: percentage of peak height to use as boundary threshold (default 5%)
    
    Returns:
        (left_idx, right_idx): indices of peak boundaries
    """
    peak_height = intensity[peak_idx]
    threshold = peak_height * (threshold_percent / 100.0)
    
    # Find left boundary (going backwards from peak)
    left = peak_idx
    while left > 0 and intensity[left] > threshold:
        left -= 1
    left = max(0, left)
    
    # Find right boundary (going forward from peak)
    right = peak_idx
    while right < len(intensity) - 1 and intensity[right] > threshold:
        right += 1
    right = min(len(intensity) - 1, right)
    
    # Ensure we have at least a few points for reliable integration
    if right - left < 2:
        left = max(0, peak_idx - 3)
        right = min(len(intensity) - 1, peak_idx + 3)
    
    return left, right


# --- Integration peaks (improved with Simpson's rule + dynamic boundaries) ---
def integrate_peaks(rt, intensity, peaks):
    """
    Integrate peaks using Simpson's rule with dynamic boundary detection.
    
    Simpson's rule is more accurate than trapezoid rule for curved peaks typical in MS data.
    Dynamic boundaries capture the full peak area instead of using fixed windows.
    """
    results = []

    for p in peaks:
        # Find dynamic boundaries based on peak decay
        left, right = find_peak_boundaries(intensity, p, threshold_percent=5)
        
        # Ensure we have at least 2 points for integration
        if right - left < 2:
            continue
        
        # Extract the segment
        rt_segment = rt[left:right+1]
        intensity_segment = intensity[left:right+1]
        
        # Use Simpson's rule for integration (more accurate than trapezoid for curved peaks)
        try:
            if len(intensity_segment) >= 2:
                # simpson() requires at least 2 points, works better with odd number of points
                area = simpson(intensity_segment, x=rt_segment)
            else:
                continue
        except:
            # Fallback to simple trapezoid if Simpson fails
            area = np.trapz(intensity_segment, rt_segment)
        
        results.append({
            "rt": rt[p],
            "area": area,
            "height": intensity[p]
        })

    return results