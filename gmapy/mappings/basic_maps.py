import warnings
import numpy as np
from scipy.sparse import csr_matrix
from .helperfuns import return_matrix



def basic_propagate(x, y, xout, interp_type='lin-lin', zero_outside=False):
    """Propagate from one mesh to another one."""
    x = np.array(x)
    y = np.array(y)
    xout = np.array(xout)
    myord = np.argsort(x)
    x = x[myord]
    y = y[myord]
    if isinstance(interp_type, str):
        interp_type = np.full(len(x), interp_type, dtype='<U7')
    interp_type = np.array(interp_type)[myord]

    possible_interp_types = ['lin-lin', 'lin-log', 'log-lin', 'log-log']
    if not np.all(np.isin(interp_type, possible_interp_types)):
        ValueError('Unspported interpolation type')

    # variable to store the result of this function
    final_yout = np.full(len(xout), 0., dtype=float)

    idcs2 = np.searchsorted(x, xout, side='left')
    idcs1 = idcs2 - 1
    # special case: where the values of xout are exactly on
    # the limits of the mesh in x
    limit_sel = np.logical_or(xout == x[0], xout == x[-1])
    not_limit_sel = np.logical_not(limit_sel)
    edge_idcs = idcs2[limit_sel]
    idcs1 = idcs1[not_limit_sel]
    idcs2 = idcs2[not_limit_sel]
    xout = xout[not_limit_sel]

    # Make sure that we actually have points that
    # need to be interpolated
    if len(idcs2) > 0:
        if np.any(idcs2 >= len(x)) and not zero_outside:
            raise ValueError('some value in xout larger than largest value in x')
        if np.any(idcs2 < 1) and not zero_outside:
            raise ValueError('some value in xout smaller than smallest value in x')

        inside_sel = np.logical_and(idcs2 < len(x), idcs2 >= 1)
        outside_sel = np.logical_not(inside_sel)
        idcs1 = idcs1[inside_sel]
        idcs2 = idcs2[inside_sel]
        xout = xout[inside_sel]

        x1 = x[idcs1]; x2 = x[idcs2]
        y1 = y[idcs1]; y2 = y[idcs2]
        xd = x2 - x1
        # transformed quantities
        log_x = np.log(x)
        log_y = np.log(y)
        log_x1 = log_x[idcs1]; log_x2 = log_x[idcs2]
        log_y1 = log_y[idcs1]; log_y2 = log_y[idcs2]
        log_xd = log_x2 - log_x1
        log_xout = np.log(xout)
        # results
        yout = {}
        yout['lin-lin'] = (y1*(x2-xout) + y2*(xout-x1)) / xd
        yout['log-lin'] = (y1*(log_x2-log_xout) + y2*(log_xout-log_x1)) / log_xd
        with warnings.catch_warnings():
            # We ignore a 'divide by zero in log warning due to y1 or y2
            # possibly containing non-positive values. As long as they
            # are not used, everything is fine. We check at the end of
            # this function explicitly for NaN values caused here.
            warnings.filterwarnings('ignore', category=RuntimeWarning)
            yout['lin-log'] = np.exp((log_y1*(x2-xout) + log_y2*(xout-x1)) / xd)
            yout['log-log'] = np.exp((log_y1*(log_x2-log_xout) + log_y2*(log_xout-log_x1)) / log_xd)

        # fill final array
        interp = interp_type[idcs1]
        interp_yout = np.full(idcs1.shape, 0.)
        for curint in possible_interp_types:
            cursel = interp == curint
            interp_yout[cursel] = yout[curint][cursel]

        tmp = np.empty(len(inside_sel), dtype=float)
        tmp[inside_sel] = interp_yout
        tmp[outside_sel] = 0.
        final_yout[not_limit_sel] = tmp

    # add the edge points
    final_yout[limit_sel] = y[edge_idcs]

    if np.any(np.isnan(final_yout)):
        raise ValueError('NaN values encountered in interpolation result')
    return final_yout



def get_basic_sensmat(x, y, xout, interp_type='lin-lin',
                      zero_outside=False, ret_mat=True):
    """Compute sensitivity matrix for basic mappings."""
    orig_x = np.array(x)
    x = orig_x.copy()
    x = np.array(x)
    y = np.array(y)
    xout = np.array(xout)
    myord = np.argsort(x)
    x = x[myord]
    y = y[myord]
    orig_len_x = len(x)
    orig_len_xout = len(xout)
    if isinstance(interp_type, str):
        interp_type = np.full(len(x), interp_type, dtype='<U7')
    interp_type = np.array(interp_type)[myord]

    possible_interp_types = ['lin-lin', 'lin-log', 'log-lin', 'log-log']
    if not np.all(np.isin(interp_type, possible_interp_types)):
        ValueError('Unspported interpolation type')

    idcs2 = np.searchsorted(x, xout, side='left')
    idcs1 = idcs2 - 1
    idcs_out = np.arange(len(xout))
    # special case: where the values of xout are exactly on
    # the limits of the mesh in x
    limit_sel = np.logical_or(xout == x[0], xout == x[-1])
    not_limit_sel = np.logical_not(limit_sel)
    edge_idcs = idcs2[limit_sel]
    edge_idcs_out = idcs_out[limit_sel]
    idcs2 = idcs2[not_limit_sel]
    idcs1 = idcs1[not_limit_sel]
    xout = xout[not_limit_sel]
    idcs_out = idcs_out[not_limit_sel]

    # initialize the index lists and
    # value list of te final sensitivity matrix
    # i ... column indices
    # j ... row indices of final sensitivity matrix
    i = []; j = []; c = []

    # Make sure that we actually have points that
    # need to be interpolated
    if len(idcs2) > 0:
        if np.any(idcs2 >= len(x)) and not zero_outside:
            raise ValueError('some value in xout larger than largest value in x')
        if np.any(idcs2 < 1) and not zero_outside:
            raise ValueError('some value in xout smaller than smallest value in x')

        inside_sel = np.logical_and(idcs2 < len(x), idcs2 >= 1)
        idcs1 = idcs1[inside_sel]
        idcs2 = idcs2[inside_sel]
        idcs_out = idcs_out[inside_sel]
        xout = xout[inside_sel]

        x1 = x[idcs1]; x2 = x[idcs2]
        y1 = y[idcs1]; y2 = y[idcs2]
        xd = x2 - x1
        # transformed quantities
        log_x = np.log(x)
        log_y = np.log(y)
        log_x1 = log_x[idcs1]; log_x2 = log_x[idcs2]
        log_y1 = log_y[idcs1]; log_y2 = log_y[idcs2]
        log_xd = log_x2 - log_x1
        log_xout = np.log(xout)
        # results
        coeffs1 = {}
        coeffs2 = {}
        # yout_linlin = (y1*(x2-xout) + y2*(xout-x1)) / xd
        coeffs1['lin-lin'] = (x2-xout) / xd
        coeffs2['lin-lin'] = (xout-x1) / xd
        # yout_loglin = (y1*(log_x2-log_xout) + y2*(log_xout-log_x1)) / log_xd
        coeffs1['log-lin'] = (log_x2-log_xout) / log_xd
        coeffs2['log-lin'] = (log_xout-log_x1) / log_xd

        with warnings.catch_warnings():
            # We ignore a 'divide by zero in log warning due to y1 or y2
            # possibly containing non-positive values. As long as they
            # are not used, everything is fine. We check at the end of
            # this function explicitly for NaN values in the sensitivity
            # matrix before it is returned.
            warnings.filterwarnings('ignore', category=RuntimeWarning)

            log_yout_linlog = (log_y1*(x2-xout) + log_y2*(xout-x1)) / xd
            coeffs1['lin-log'] = np.exp(-log_y1 + np.log((x2-xout)/xd) + log_yout_linlog)
            coeffs2['lin-log'] = np.exp(-log_y2 + np.log((xout-x1)/xd) + log_yout_linlog)

            log_yout_loglog = (log_y1*(log_x2-log_xout) + log_y2*(log_xout-log_x1)) / log_xd
            coeffs1['log-log'] = np.exp(-log_y1 + np.log((log_x2-log_xout)/log_xd) + log_yout_loglog)
            coeffs2['log-log'] = np.exp(-log_y2 + np.log((log_xout-log_x1)/log_xd) + log_yout_loglog)

        interp = interp_type[idcs1]
        for curint in possible_interp_types:
            cursel = interp == curint
            # coeff1
            i.append(idcs1[cursel])
            j.append(idcs_out[cursel])
            c.append(coeffs1[curint][cursel])
            # coeff2
            i.append(idcs2[cursel])
            j.append(idcs_out[cursel])
            c.append(coeffs2[curint][cursel])

    # deal with sensitivies for values at the mesh edges
    i.append(np.concatenate([edge_idcs, edge_idcs]))
    j.append(np.concatenate([edge_idcs_out, edge_idcs_out]))
    c.append(np.concatenate([np.full(edge_idcs.shape, 1.),
                             np.full(edge_idcs.shape, 0.)]))

    # better than model casting:
    # flatten the list of arrays to a single array
    i = myord[np.concatenate(i)]
    j = np.concatenate(j)
    c = np.concatenate(c)
    # we sort these arrays according to j to ensure
    # that the coefficients in one row of the sensitivity
    # matrix are consecutive elements in the array c.
    # We have two coefficients per row irrespective of
    # the interpolation law.
    # The function basic_multiply_Sdic_rows relies on
    # this assumption.
    perm = np.argsort(j)
    i = i[perm]
    j = j[perm]
    c = c[perm]
    # We further do swaps of the variables associated
    # with a row j if x[j_k] > x[j_(k+1)], to be sure
    # that the coefficient associated with the lower x-value
    # comes first. The function basic_extract_Sdic_coeffs
    # relies on this structure.
    i_tmp = i.copy()
    c_tmp = c.copy()
    should_swap = orig_x[i[::2]] > orig_x[i[1::2]]
    i[::2] = np.where(should_swap, i_tmp[1::2], i_tmp[::2])
    i[1::2] = np.where(should_swap, i_tmp[::2], i_tmp[1::2])
    c[::2] = np.where(should_swap, c_tmp[1::2], c_tmp[::2])
    c[1::2] = np.where(should_swap, c_tmp[::2], c_tmp[1::2])

    if np.any(np.isnan(c)):
        raise ValueError('NaN values encountered in Jacobian matrix')

    return return_matrix(i, j, c, dims=(orig_len_xout, orig_len_x),
                         how='csr' if ret_mat else 'dic')



def basic_multiply_Sdic_rows(Sdic, rowfacts):
    """Multiply each row with a multiplication factor.

    Multiply each row of a sensitivity matrix returned
    by get_basic_sensmat function as a dictionary with a
    multiplication factor. The dictionary Sdic is changed
    in place.
    """
    Sdic['x'][::2] *= rowfacts
    Sdic['x'][1::2] *= rowfacts



def basic_extract_Sdic_coeffs(Sdic):
    """Extract partial derivatives from Sdic.

    Sdic represents the sensitivity matrix S
    to map from y-values given on mesh x to
    a mesh xout. Only two non-zero values
    are present in each row of S which are
    the partial derivative with respect to
    the y-value at the lower and upper limit
    of an interval respectively. This function
    facilitates the extraction of these
    partial derivatives.
    """
    df_da = Sdic['x'][::2].copy()
    df_db = Sdic['x'][1::2].copy()
    return [df_da, df_db]



def basic_product_propagate(xlist, ylist, xout, interplist,
                            zero_outside=False, **kwargs):
    """Propagate the product of two basic maps."""
    if len(xlist) != len(ylist) or len(ylist) != len(interplist):
        raise IndexError('xlist, ylist and interplist must have ' +
                         'the same number of elements')
    prod = 1.
    for x, y, interp in zip(xlist, ylist, interplist):
        prod *= basic_propagate(x, y, xout, interp, zero_outside, **kwargs)
    return prod



def get_basic_product_sensmats(xlist, ylist, xout, interplist,
                              zero_outside=False, ret_mat=True, **kwargs):
    """Get a list of Jacobians for each factor in a product of basic maps."""
    if len(xlist) != len(ylist) or len(ylist) != len(interplist):
        raise IndexError('xlist, ylist and interplist must have ' +
                         'the same number of elements')
    proplist = []
    for x, y, interp in zip(xlist, ylist, interplist):
        proplist.append(basic_propagate(x, y, xout, interp,
                        zero_outside, **kwargs))
    proparr = np.stack(proplist, axis=0)

    Slist = []
    for i, (x, y, interp) in enumerate(zip(xlist, ylist, interplist)):
        curSdic = get_basic_sensmat(x, y, xout, interp, zero_outside,
                                    ret_mat=False, **kwargs)
        sel = np.logical_and(np.min(x) <= xout, np.max(x) >= xout)
        curfacts = np.prod(proparr[:i,:], axis=0)
        if i+1 < proparr.shape[0]:
            curfacts *= np.prod(proparr[(i+1):,:], axis=0)
        basic_multiply_Sdic_rows(curSdic, curfacts[sel])
        Slist.append(curSdic)

    if ret_mat:
        for i in range(len(Slist)):
            curS = Slist[i]
            curS = return_matrix(curS['idcs1'], curS['idcs2'], curS['x'],
                                 dims=(len(xout), len(xlist[i])), how='csr')
            Slist[i] = curS

    return Slist
