# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2021, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .SBAS_base import SBAS_base
from .PRM import PRM

class SBAS_prm(SBAS_base):

    def PRM(self, subswath=None, date=None, multi=True, singleswath=False):
        """
        Open a PRM (Parameter) file.

        Parameters
        ----------
        subswath : int, optional
            The subswath number. If None, return a single subswath PRM file. Default is None.
        date : str, optional
            The date of the PRM file. If None or equal to self.reference, return the reference PRM file. Default is None.
        multi : bool, optional
            If True, open a multistem PRM file. If False, open a stem PRM file. Default is True.
        singleswath : bool, optional
            If True, open a single-digit subswath PRM file instead of a merged (multi-digit) one. Default is False.

        Returns
        -------
        PRM
            An instance of the PRM class representing the opened PRM file.
        """
        import os

        # check if subswath exists or return a single subswath for None
        subswath = self.get_subswath(subswath)

        if date is None or date == self.reference:
            line = self.get_reference(subswath)
        else:
            line = self.get_repeat(subswath, date)
        #print (line)
        # to build sbas table and pairs after merging use unmerged subswath PRM files
        if singleswath and len(str(subswath))>1:
            subswath = int(str(subswath)[0])
        multistem, stem = self.multistem_stem(subswath, line.datetime[0])
        if multi:
            stem = multistem
        filename = os.path.join(self.basedir, f'{stem}.PRM')
        #print (filename)
        return PRM.from_file(filename)