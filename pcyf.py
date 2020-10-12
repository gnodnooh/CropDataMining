"""
This script presents algorithms of probabilistic crop yield forecast (PCYF) model.

File name: pcyf.py
Date revised: 10/11/2020
"""
__version__ = "1.0"
__author__ = "Donghoon Lee"
__maintainer__ = "Donghoon Lee"
__email__ = "dlee@geog.ucsb.edu"


from itertools import compress, product, combinations
import time
import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd
pd.options.mode.chained_assignment = None
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, PredefinedSplit, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import mean_squared_error
import metrics as mt


class PCYF:
    '''
    
    Description will be updated.
    '''
    
    def __init__(self, dfCrop, dfPred, targmon, leadmat, pid=None):
        # Model parameters
        monmat = self._LeadToMonth(targmon, leadmat)
        dfCrop = dfCrop[dfCrop.index[dfCrop.index.month == targmon]]
        dfCrop = dfCrop.drop(dfCrop[dfCrop.isnull()].index,axis=0)          # Drop missing years

        obox = dict({'pid':pid, 'status':0})
        # STATUS_CODE 110: The number of years less than 15
        if len(dfCrop) < 15:
            obox['status'] = 110                        # STATUS_CODE
            obox['status_msg'] = 'The number of records is less than 15.'
            self.outbox = obox
            return
        # STATUS_CODE 120: Monotonic values (possible missing records)
        if dfCrop.is_monotonic:
            obox['status'] = 120                        # STATUS_CODE
            obox['status_msg'] = 'The records are monotonic.'
            self.outbox = obox
            return

            
        # Split data for training and testing
        yTRAN, yTEST = train_test_split(dfCrop, test_size=0.30, shuffle=False)
        nt = len(yTEST)
        obs = np.zeros([nt,len(leadmat)])
        sim = np.zeros([nt,len(leadmat)])
        
        # Prediction algorithms
        for i in range(len(leadmat)):
            lead = leadmat[:i+1]
            # Initialize the monthly box
            mbox = {'lead':lead[i], 'month':monmat[i]}
            result = np.zeros([nt, 1])
            for j in range(nt):
                yTran = pd.concat([yTRAN,yTEST.iloc[:j]])
                yTest = yTEST.iloc[j:j+1]
                tdx = pd.concat([yTran,yTest]).index

                # Correlations with EO data at all possible lead-time combinations
                prcp, prcp_monmat = self._AllCombLeadMonth(dfPred['prcp'], tdx, lead)
                prcp_corr, prcp_sign = self._Corr2D1D(prcp[:-1,:], yTran)
                smos, smos_monmat = self._AllCombLeadMonth(dfPred['smos'], tdx, lead)
                smos_corr, smos_sign = self._Corr2D1D(smos[:-1,:], yTran)
                etos, etos_monmat = self._AllCombLeadMonth(dfPred['etos'], tdx, lead)
                etos_corr, etos_sign = self._Corr2D1D(etos[:-1,:], yTran)

                # Select the best combination of leadtimes (SHOULD BE UPDATED)
                strPred = ['prcp','smos','etos']
                iprcp = prcp_corr.argmax()
                ismos = smos_corr.argmax()
                ietos = smos_corr.argmin()
                pred = np.vstack((prcp[:,iprcp], smos[:,ismos], etos[:,ietos])).T
                pred_monmat = [prcp_monmat[iprcp], smos_monmat[ismos], etos_monmat[ietos]]
                xTran = pd.DataFrame(index = tdx.year, data=pred, columns = strPred)
                xTest = xTran.iloc[-1]
                xTran = xTran.iloc[:-1]

                # Nomalize before prediction
                scale_x = StandardScaler().fit(xTran)
                scale_x.scale_ = np.std(xTran, axis=0, ddof=1)        # Sample STDEV
                xTran = scale_x.transform(xTran)
                xTest = scale_x.transform(xTest.values[:,None].T)
                scale_y = StandardScaler().fit(yTran.values[:,None])
                scale_y.scale_ = np.std(yTran, axis=0, ddof=1)        # Sample STDEV
                yTran = scale_y.transform(yTran.values[:,None])
                yTest = scale_y.transform(yTest.values[:,None])

                # Multiple Linear Regression (MLR)
                regr = LinearRegression()
                regr.fit(xTran, yTran)
                yTranHat = regr.predict(xTran)
                yTestHat = regr.predict(xTest)

                # Re-scaling
                xTran = scale_x.inverse_transform(xTran)
                xTest = scale_x.inverse_transform(xTest)
                yTran = scale_y.inverse_transform(yTran)
                yTest = scale_y.inverse_transform(yTest)
                yTranHat = scale_y.inverse_transform(yTranHat)
                yTestHat = scale_y.inverse_transform(yTestHat)

                # Save results
                obs[j,i] = yTest
                sim[j,i] = yTestHat
                result[j] = yTestHat
                


            # Evaluating statiscis: gss, msess
            table = mt.makeMultiContTable(yTEST.values[:,None].T, result.T, clm=yTRAN, thrsd=[1/3, 2/3])
            mct = mt.MulticlassContingencyTable(table, n_classes=3)
            gss = mct.gerrity_skill_score()
            msess = mt.msess(yTEST, result, yTRAN)

            # Update monthly box
            mbox.update({'regr': regr,
                         'yTran': yTRAN,
                         'yTest': yTEST, 'yTestHat': result,
                         'gss':gss, 'msess':msess
                        })

            # Save lead box
            obox.update({'m%02d'%(lead[i]): mbox})
#             print('%s - m%02d is processed.' % (pid, lead[i]))

    
        self.outbox = obox
            
            
            
    
    def _Detrend(self, ssr):
        '''detrends 1D Series

        *this function deals with missing values.

        Parameters
        ----------
        sr: Series
            time-series to be detrended

        Returns
        -------
        sr: Series
            detrended values of the time-series

        '''
        nni = ~sr.isnull()
        if False:
            # Considering NaN values
            x = np.array((sr.index - sr.index[0])/12 + 1, dtype='int')
            m, b, r_val, p_val, std_err = stats.linregress(x[nni], sr[nni])
            sr_detrend = sr - (m*x +b)
        else:
            # Ignoring NaN values
            from scipy import signal
            sr_detrend = sr.copy()
            sr_detrend[nni] = pd.Series(signal.detrend(sr[nni]), index = sr[nni].index)

        return sr_detrend


    def _ReduceMonth(self, sr, i):
        sr = sr[sr.index[sr.index.month == i]]
        sr.index = sr.index.year
        return sr


    def _ReduceSeason(self, sr, monmat, name):
        df = sr[sr.index[sr.index.month.isin(monmat)]].to_frame()
        df['month'] = df.index.month
        df['year'] = df.index.year
        df = df.pivot(index='year', columns='month', values=name)
        df.columns.name= None
        df.columns = ['%s_mo_%02d' % (name, mo) for mo in monmat]
        return df


    def _AllCombinations(self, lst):
        combs = []
        for i in range(1, len(lst)+1):
            els = [list(x) for x in combinations(lst, i)]
            combs.extend(els)
        combs
        return combs


    def _LeadToMonth(self, targmon, leadmat):
        monmat = targmon - np.array(leadmat)
        monmat[monmat <=0] = monmat[monmat <=0] + 12
        return monmat


    def _AllCombLeadMonth(self, sr, time, leadmat):
        # All combinations of lead months
        combs = self._AllCombinations(leadmat)

        # Ndarray of summation of data of all combinations of lead months
        data_sum = np.zeros([len(time), len(combs)])
        for i, comb in enumerate(combs):
            data_com = np.zeros([len(time), len(comb)])
            for j, m in enumerate(comb):
                data_com[:,j] = sr[time - MonthEnd(m)].values
            data_sum[:,i] = data_com.sum(1)

        # Change leadmat to monthmat
        monmat = self._LeadToMonth(time.month.unique()[0], leadmat)
        combs = self._AllCombinations(list(monmat))

        return data_sum, combs

    def _Corr2D1D(self, arr2d, arr1d):
        corr = np.zeros(arr2d.shape[1])
        sign = corr.copy()
        for i in range(arr2d.shape[1]):
            corr[i], sign[i] = stats.pearsonr(arr2d[:,i], arr1d)
        return corr, sign