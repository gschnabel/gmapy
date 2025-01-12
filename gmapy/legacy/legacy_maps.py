import numpy as np


def propagate_fisavg(ens, vals, ensfis, valsfis, check_norm=True):
    ord = np.argsort(ens)
    ens = ens[ord]
    vals = vals[ord]
    ordfis = np.argsort(ensfis)
    ensfis = ensfis[ordfis]
    valsfis = valsfis[ordfis]

    # we skip one element, because all energy meshes contain
    # as lowest energy 2.53e-8 MeV
    fidx = np.searchsorted(ensfis[1:], ens[1]) + 1

    ensfis = np.concatenate([ensfis, np.full(100, 0.)])
    valsfis = np.concatenate([valsfis, np.full(100, 0.)])

    uhypidx = fidx+len(ens)-1
    urealidx = min(fidx+len(ens)-1, len(ensfis))
    ulimidx2 = len(ens) - (uhypidx - urealidx)
    # TODO: This check fails for the 9Pu(n,f) cross section fission average
    #       because the energy 0.235 MeV is missing in 9Pu(n,f) but present
    #       in the fission spectrum
    # if not np.all(np.isclose(ens[1:ulimidx2], ensfis[fidx:urealidx], atol=0, rtol=1e-05)):
    #   raise ValueError('energies of excitation function and fission spectrum do not match')

    fl = 0.
    sfl = 0.
    for i in range(1, ulimidx2-1):
        fl = fl + valsfis[fidx-1+i]
        el1 = 0.5 * (ens[i-1] + ens[i])
        el2 = 0.5 * (ens[i] + ens[i+1])
        de1 = 0.5 * (ens[i] - el1)
        de2 = 0.5 * (el2 - ens[i])
        ss1 = 0.5 * (vals[i] + 0.5*(vals[i-1] + vals[i]))
        ss2 = 0.5 * (vals[i] + 0.5*(vals[i] + vals[i+1]))
        cssli = (ss1*de1 + ss2*de2) / (de1+de2)
        sfl = sfl + cssli*valsfis[fidx-1+i]

    fl = fl + valsfis[0] + valsfis[urealidx-1]
    sfl = sfl + valsfis[0]*vals[0] + valsfis[urealidx-1]*vals[-1]
    sfis = sfl / fl

    if check_norm and not np.isclose(1., fl, atol=0, rtol=1e-4):
        print('fission normalization: ' + str(fl))
        raise ValueError('fission spectrum not normalized')

    return sfis


def get_sensmat_fisavg(ens, vals, ensfis, valsfis):
    """SACS Jacobian according to legacy code (wrong)."""
    ord = np.argsort(ens)
    ens = ens[ord]
    vals = vals[ord]
    ordfis = np.argsort(ensfis)
    ensfis = ensfis[ordfis]
    valsfis = valsfis[ordfis]

    # we skip one element, because all energy meshes contain
    # as lowest energy 2.53e-8 MeV
    fidx = np.searchsorted(ensfis[1:], ens[1]) + 1

    # TODO: This check fails for the 9Pu(n,f) cross section fission average
    #       because the energy 0.235 MeV is missing in 9Pu(n,f) but present
    #       in the fission spectrum
    # if not np.all(np.isclose(ens[1:ulimidx2], ensfis[fidx:urealidx], atol=0, rtol=1e-05)):
    #     raise ValueError('energies of excitation function and fission spectrum do not match')

    ensfis = np.concatenate([ensfis, np.full(100, 0.)])
    valsfis = np.concatenate([valsfis, np.full(100, 0.)])

    sensvec = np.full(len(ens), 0., dtype=float)

    fl = 0.
    for i in range(0, len(ens)):
        fl = fl + valsfis[fidx+i]
        if i == 0 or i == len(ens)-1:
            cssj = vals[i]
        else:
            el1 = 0.5 * (ens[i-1] + ens[i])
            el2 = 0.5 * (ens[i] + ens[i+1])
            de1 = 0.5 * (ens[i] - el1)
            de2 = 0.5 * (el2 - ens[i])
            ss1 = 0.5 * (vals[i] + 0.5*(vals[i-1] + vals[i]))
            ss2 = 0.5 * (vals[i] + 0.5*(vals[i] + vals[i+1]))
            cssj = (ss1*de1 + ss2*de2) / (de1+de2)

        sensvec[i] = valsfis[fidx+i-1] * cssj / vals[i]

    sensvec[ord] = sensvec.copy()
    return sensvec


def get_sensmat_fisavg_corrected(ens, vals, ensfis, valsfis, check_norm=True):
    """Correct SACS Jacobian calculation."""
    ord = np.argsort(ens)
    ens = ens[ord]
    vals = vals[ord]
    ordfis = np.argsort(ensfis)
    ensfis = ensfis[ordfis]
    valsfis = valsfis[ordfis]

    # we skip one element, because all energy meshes contain
    # as lowest energy 2.53e-8 MeV
    fidx = np.searchsorted(ensfis[1:], ens[1]) + 1

    ensfis = np.concatenate([ensfis, np.full(100, 0.)])
    valsfis = np.concatenate([valsfis, np.full(100, 0.)])

    uhypidx = fidx+len(ens)-1
    urealidx = min(fidx+len(ens)-1, len(ensfis))
    ulimidx2 = len(ens) - (uhypidx - urealidx)
    # TODO: This check fails for the 9Pu(n,f) cross section fission average
    #       because the energy 0.235 MeV is missing in 9Pu(n,f) but present
    #       in the fission spectrum
    # if not np.all(np.isclose(ens[1:ulimidx2], ensfis[fidx:urealidx], atol=0, rtol=1e-05)):
    #   raise ValueError('energies of excitation function and fission spectrum do not match')

    fl = 0.
    sensvec = np.full(len(vals), 0., dtype=float)
    for i in range(1, ulimidx2-1):
        fl = fl + valsfis[fidx-1+i]
        el1 = 0.5 * (ens[i-1] + ens[i])
        el2 = 0.5 * (ens[i] + ens[i+1])
        de1 = 0.5 * (ens[i] - el1)
        de2 = 0.5 * (el2 - ens[i])
        # For reference: the following lines for propagation
        # appear in propagate_fisavg and are the basis for
        # the sensitivity matrix calculation
        # ss1 = 0.5 * (vals[i] + 0.5*(vals[i-1] + vals[i]))
        # ss2 = 0.5 * (vals[i] + 0.5*(vals[i] + vals[i+1]))
        # cssli = (ss1*de1 + ss2*de2) / (de1+de2)
        # sfl = sfl + cssli*valsfis[fidx-1+i]
        ss1di = 0.75
        ss1dim1 = 0.25
        ss2di = 0.75
        ss2dip1 = 0.25
        coeff1 = de1/(de1+de2) * valsfis[fidx-1+i]
        coeff2 = de2/(de1+de2) * valsfis[fidx-1+i]
        sensvec[i] += ss1di * coeff1 + ss2di * coeff2
        sensvec[i-1] += ss1dim1 * coeff1
        sensvec[i+1] += ss2dip1 * coeff2

    fl = fl + valsfis[0] + valsfis[urealidx-1]
    # For reference: the renormalization of the propagated value
    # due to a potentially not normalized fission spectrum
    # sfl = sfl + valsfis[0]*vals[0] + valsfis[urealidx-1]*vals[-1]
    # sfis = sfl / fl
    sensvec[0] += valsfis[0]
    sensvec[-1] += valsfis[urealidx-1]
    sensvec /= fl

    if check_norm and not np.isclose(1., fl, atol=0, rtol=1e-4):
        print('fission normalization: ' + str(fl))
        raise ValueError('fission spectrum not normalized')

    sensvec[ord] = sensvec.copy()
    return sensvec
