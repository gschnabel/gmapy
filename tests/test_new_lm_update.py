import unittest
import pathlib
import pandas as pd
import numpy as np
from scipy.sparse import block_diag, diags
from gmapy.data_management.tablefuns import (
    create_prior_table,
    create_experiment_table)
from gmapy.data_management.uncfuns import create_experimental_covmat
from gmapy.mappings.priortools import (
    prepare_prior_and_exptable,
    attach_shape_prior,
    initialize_shape_prior,
    remove_dummy_datasets
)
from gmapy.inference import (
    lm_update,
    new_lm_update,
)
from gmapy.mcmc_inference import Posterior
from gmapy.data_management.database_IO import read_legacy_gma_database
from gmapy.mappings.compound_map import CompoundMap
from gmapy.data_management.uncfuns import create_relunc_vector


class TestNewLevenbergMarquardtUpdate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        dbpath = (pathlib.Path(__file__).parent / 'testdata' /
                'data-2017-07-26.gma').resolve().as_posix()
        db_dic = read_legacy_gma_database(dbpath)
        prior_list = db_dic['prior_list']
        datablock_list = db_dic['datablock_list']
        remove_dummy_datasets(datablock_list)

        priortable = create_prior_table(prior_list)
        priorcov = diags(np.square(priortable['UNC']), format='csc')

        exptable = create_experiment_table(datablock_list)
        expcov = create_experimental_covmat(datablock_list)

        datatable = pd.concat([priortable, exptable], axis=0, ignore_index=True)
        datatable = attach_shape_prior(datatable)

        # the following block to prepare all the quantities
        # to call attach_shape_prior
        expsel = datatable['NODE'].str.match('exp_').to_numpy()
        refvals = datatable['PRIOR']
        reluncs = np.full(len(refvals), np.nan)
        reluncs[expsel] = create_relunc_vector(datablock_list)
        compmap = CompoundMap()
        initialize_shape_prior(datatable, compmap, refvals, reluncs)

        shapecov = diags(np.full(len(datatable)-len(priortable)-len(exptable), np.inf), format='csc')
        totcov = block_diag([priorcov, expcov, shapecov], format='csc')
        cls._dbpath = dbpath
        cls._datatable = datatable
        cls._totcov = totcov

    def test_new_lm_update_equivalent_lm_update(self):
        datatable = self._datatable
        totcov = self._totcov
        priortable, exptable, _, _ = prepare_prior_and_exptable(
            datatable, True, reset_index=False
        )
        prior_idcs = np.array(priortable.index)
        prior_idcs_map = {j: i for i, j in enumerate(prior_idcs)}
        priorvals = priortable['PRIOR'].to_numpy(copy=True)
        expvals = exptable['DATA'].to_numpy(copy=True)
        priorcov = totcov[:, priortable.index][priortable.index, :]
        expcov = totcov[:, exptable.index][exptable.index, :]
        compmap1 = CompoundMap()
        compmap2 = CompoundMap(datatable, reduce=True)
        postdist = Posterior(priorvals, priorcov, compmap2, expvals, expcov) 
        r1 = lm_update(
            compmap1, datatable, totcov, retcov=False, print_status=True
        )
        real_idcs = np.array([prior_idcs_map[idcs] for idcs in r1['idcs']])
        res1 = priorvals.copy()
        res1[real_idcs] = r1['upd_vals']
        print('\n\n----------------------------------------\n\n')
        r2 = new_lm_update(postdist, print_status=True)
        res2 = r2['upd_vals']
        self.assertTrue(np.allclose(res1, res2, atol=1e-12, rtol=1e-12))


if __name__ == '__main__':
    unittest.main()