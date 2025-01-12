import numpy as np
import pandas as pd
from .mapping_elements import (
    InputSelectorCollection,
    Selector,
    Distributor,
    SumOfDistributors
)
from .priortools import prepare_prior_and_exptable


class RelativeErrorMap:

    def __init__(self, datatable, distributor_like,
                 selcol=None, distsum=None, reduce=False):
        if type(distributor_like) not in (Distributor, SumOfDistributors):
            raise TypeError('distributor_like must be of class Distributor '
                            'or class SumOfDistributors')
        self.__numrows = len(datatable)
        if selcol is None:
            selcol = InputSelectorCollection()
        self.__input, self.__output = self.__prepare(
            datatable, distributor_like, selcol, reduce
        )
        if distsum is not None:
            distsum.add_distributors(self.__output.get_distributors())

    def is_responsible(self):
        ret = np.full(self.__numrows, False)
        if self.__output is not None:
            idcs = self.__output.get_indices()
            ret[idcs] = True
        return ret

    def propagate(self, refvals):
        self.__input.assign(refvals)
        return self.__output.evaluate()

    def jacobian(self, refvals):
        self.__input.assign(refvals)
        return self.__output.jacobian()

    def get_selectors(self):
        return self.__input.get_selectors()

    def get_distributors(self):
        return self.__output.get_distributors()

    def __prepare(self, datatable, distributor_like, selcol, reduce):
        priortable, exptable, src_len, tar_len = \
            prepare_prior_and_exptable(datatable, reduce)

        priormask = priortable['NODE'].str.match('relerr_', na=False)
        priortable = priortable[priormask]
        expmask = exptable['NODE'].str.match('exp_', na=False)
        exptable = exptable[expmask]

        inp = InputSelectorCollection()
        out = SumOfDistributors()
        if len(priortable) == 0 or len(exptable) == 0:
            return inp, out

        # determine the source and target indices of the mapping
        expids = exptable['NODE'].str.extract(r'exp_([0-9]+)$')
        ptidx = exptable['PTIDX']
        rerr_expids = priortable['NODE'].str.extract(r'relerr_([0-9]+)$')
        rerr_ptidx = priortable['PTIDX']
        mapdf1 = pd.concat([expids, ptidx], axis=1)
        mapdf1.columns = ('expid', 'ptidx')
        mapdf1.reset_index(inplace=True, drop=False)
        mapdf1.set_index(['expid', 'ptidx'], inplace=True)
        mapdf2 = pd.concat([rerr_expids, rerr_ptidx], axis=1)
        mapdf2.columns = ('expid', 'ptidx')
        mapdf2.reset_index(inplace=True, drop=False)
        mapdf2.set_index(['expid', 'ptidx'], inplace=True)
        source_indices = mapdf2['index'].to_numpy()
        target_indices = mapdf1.loc[list(mapdf2.index), 'index'].to_numpy()
        # construct the selectors
        if type(distributor_like) == SumOfDistributors:
            aux_dists = distributor_like.get_distributors()
        else:
            aux_dists = [distributor_like]
        aux_distsum = SumOfDistributors(aux_dists)

        relerrors = selcol.define_selector(source_indices, src_len)
        expquants = Selector(aux_distsum, target_indices)
        abserrors = relerrors * expquants
        abserrors_dist = Distributor(abserrors, target_indices, tar_len)

        inp.add_selector(relerrors)
        out.add_distributor(abserrors_dist)
        return inp, out


def attach_relative_error_df(datatable):
    dt = datatable.copy()
    dt.sort_index()
    groupidx_df = dt.groupby('NODE').cumcount().to_frame(name='PTIDX')
    dt = pd.concat([dt, groupidx_df], axis=1)
    # create the relative errors dataframe
    isexp = dt['NODE'].str.match('exp_')
    relerr_dt = dt[isexp][['NODE', 'PTIDX', 'REAC', 'ENERGY']].copy()
    relerr_dt['NODE'] = relerr_dt['NODE'].str.replace('exp_', 'relerr_',
                                                      regex=False)
    relerr_dt['PRIOR'] = np.full(len(relerr_dt), 0.)
    # combine the two
    dt = pd.concat([dt, relerr_dt], axis=0, ignore_index=True)
    return dt
