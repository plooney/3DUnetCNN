import numpy as np
from nilearn.image.image import check_niimg
from nilearn.image.image import _crop_img_to as crop_img_to


def crop_img(img, rtol=1e-8, copy=True, return_slices=False, pad=True, percentile=None, return_affine=False):
    """Crops img as much as possible
    Will crop img, removing as many zero entries as possible
    without touching non-zero entries. Will leave one voxel of
    zero padding around the obtained non-zero area in order to
    avoid sampling issues later on.
    Parameters
    ----------
    img: Niimg-like object
        See http://nilearn.github.io/manipulating_images/input_output.html
        img to be cropped.
    rtol: float
        relative tolerance (with respect to maximal absolute
        value of the image), under which values are considered
        negligeable and thus croppable.
    copy: boolean
        Specifies whether cropped data is copied or not.
    return_slices: boolean
        If True, the slices that define the cropped image will be returned.
    pad: boolean
        If True, an extra slice in each direction will be added to the image
    percentile: integer or None
        If not None, then the image will be crop out slices below the given percentile
    Returns
    -------
    cropped_img: image
        Cropped version of the input image
    """

    img = check_niimg(img)
    data = img.get_data()
    if percentile is not None:
        passes_threshold = data > np.percentile(data, percentile)
    else:
        infinity_norm = max(-data.min(), data.max())
        passes_threshold = np.logical_or(data < -rtol * infinity_norm,
                                         data > rtol * infinity_norm)

    if data.ndim == 4:
        passes_threshold = np.any(passes_threshold, axis=-1)
    coords = np.array(np.where(passes_threshold))
    start = coords.min(axis=1)
    end = coords.max(axis=1) + 1

    if pad:
        # pad with one voxel to avoid resampling problems
        start = np.maximum(start - 1, 0)
        end = np.minimum(end + 1, data.shape[:3])

    slices = [slice(s, e) for s, e in zip(start, end)]

    if return_slices:
        return slices

    if return_affine:
        return image_slices_to_affine(img, slices), end - start

    return crop_img_to(img, slices, copy=copy)


def image_slices_to_affine(image, slices):
    affine = image.affine

    linear_part = affine[:3, :3]
    old_origin = affine[:3, 3]
    new_origin_voxel = np.array([s.start for s in slices])
    new_origin = old_origin + linear_part.dot(new_origin_voxel)

    new_affine = np.eye(4)
    new_affine[:3, :3] = linear_part
    new_affine[:3, 3] = new_origin
    return new_affine


def run_with_background_correction(func, image, background=None, returns_array=False, reset_background=True,
                                   axis=(-3, -2, -1), **kwargs):
    data = image.get_data()
    if background is None:
        background = get_background_values(data, axis=axis)

    # set background to zero
    data[:] -= background
    # perform function on image
    image = func(image, **kwargs)
    # set the background back to what it was originally
    if reset_background:
        if returns_array:
            # the function called should have returned an array
            data = image
        else:
            # the function called should have returned an image
            data = image.get_data()
        data[:] += background
    return image


def get_background_values(data, axis=(-3, -2, -1)):
    background = data.min(axis=axis)
    if isinstance(background, np.ndarray):
        while len(background.shape) < len(data.shape):
            background = background[..., None]
    return background
