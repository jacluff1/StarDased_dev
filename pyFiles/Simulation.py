
#===============================================================================#
# import internal dependencies                                                  #
#===============================================================================#

from BaseClass import BaseClass
from Input import radiusParams, thetaParams, phiParams, massParams, speedParams, maxT

import Functions as fun

#===============================================================================#
# import external dependencies                                                  #
#===============================================================================#

import numpy as np
import pandas as pd
import pdb

#===============================================================================#
# Simulation definition                                                         #
#===============================================================================#

class Simulation( BaseClass ):

    #===========================================================================#
    # constructor                                                               #
    #===========================================================================#

    def __init__( self, *args, **kwargs ):
        """
        use:
        creates an instance of Simulation. defines a factor space based on
        params defined in Input.py. If the sim has not been previously run, will
        create an empty DataFrame to hold all the sim data.

        ============================================================================
        input:          type:           description:
        ============================================================================
        args:           type:           description:

        kwargs:         type:           description:
        verbose         bool            flag to print, default = False

        ============================================================================
        output:         type:
        ============================================================================
        None            None
        """

        # construct smaller set of kwargs used for construction
        kwargs1 = {}
        if 'verbose' in kwargs: kwargs1['verbose'] = kwargs['verbose']

        # run BaseClass constructor for Simulation instance
        super().__init__( "Simulation", *args, **kwargs )

    #===========================================================================#
    # public methods                                                            #
    #===========================================================================#

    #===========================================================================#
    # puplic methods                                                            #
    # required for BaseClass, implemented here                                  #
    #===========================================================================#

    #===========================================================================#
    # semi-protected methods                                                    #
    #===========================================================================#

    #===========================================================================#
    # semi-protected methods                                                    #
    # required for BaseClass, implemented here                                  #
    #===========================================================================#

    def _generateEmptyData( self, **kwargs ):
        """
        use:
        Method shall add an empty pd.DataFrame, accessed by self.data_. the
        DataFrame will hold all the generated data from all the random walks
        from all the initial states defined in the generated sample ( found in
        self.sample_ )

        ============================================================================
        input:          type:           description:
        ============================================================================
        args:           type:           description:

        kwargs:         type:           description:
        verbose         bool            flag to print, default = False

        ============================================================================
        output:         type:
        ============================================================================
        None            None
        """
        self.data_ = pd.DataFrame( columns=self.columns_ )

    def _generateSampleSpace( self, **kwargs ):
        """
        use:
        Method shall add a dictionary, accessed by self.factorSpace_, where the keys
        are the sampleFactors and the values are np.arrays of all allowed values
        included in the factor space.

        The keys in sampleFactors_ must remain constant, but it is allowed to
        adjust the factor space (for example, expand the factor space, narrow it
        down around a percieved richer space, etc..). Every time the model is
        instantiated, it will retain its previous runs and re-set up the factor
        space it is considering.

        ============================================================================
        input:          type:           description:
        ============================================================================
        args:           type:           description:

        kwargs:         type:           description:
        verbose         bool            flag to print, default = False

        ============================================================================
        output:         type:
        ============================================================================
        None            None
        """

        self.sampleSpace_ = {
            # having radii in exponential space will allow denser sampling
            # at small radii and sparser sampling at the upper limits of radii
            # this assumes that smaller radii from CM is more likely.
            'radius'    : np.exp( -np.linspace(
            np.log( radiusParams[0] ),
            np.log( radiusParams[1] ),
            radiusParams[2]
            )),
            'theta'     : np.linspace( *thetaParams, endpoint=False ),
            'phi'       : np.linspace( *phiParams  , endpoint=False ),
            'mass'      : np.linspace( *massParams )
        }

        lines = [
            "",
            'Sample Space:',
            f"radius:\t{radiusParams}",
            f"theta:\t{thetaParams}",
            f"phi:\t{phiParams}",
            f"mass:\t{massParams}"
        ]
        fun.printHeader( *lines, **kwargs )

    def _runMonteCarloScenario( self, **kwargs ):

        # use the sampleRowIdx to get treatement values
        sampleRow = self.sample_.iloc[ self.sampleRowIdx_ ]

        # extract SPC positions from sampleRow
        spc_i3 = np.zeros( (3,3) )
        for starIdx in [ 0, 1, 2 ]:
            for colIdx, name in enumerate([ 'radius', 'theta', 'phi' ]):
                key = f"{name}_({starIdx},0)"
                spc_i3[ starIdx, colIdx ] = sampleRow[ key ]

        # extract masses from sampleRow
        m_i1 = np.array([ sampleRow[ f"mass_({starIdx})" ] for starIdx in range(3) ])[:,None]

        # calculate XYZ positions
        x_i3 = fun.spc2xyz( spc_i3, **kwargs )

        # calculate CM of the new system ( vector from current origin to CM )
        CM_13 = fun.findCM( x_i3, m_i1 )

        # make CM the new origin ( subtract CM vector from star positions )
        x_i3 -= CM_13

        # calculate escape velocity from system
        escapeSpeed_i1 = fun.escapeSpeed( posXYZ, M )

        # create container to hold spc initial velocities
        spcdot_i3 = np.zeros( (3,3) )
        # assign random speed
        spcdot_i3[ : , 0 ] = fun.randomVelSPC( escapeSpeed_i1 )
        # fill in the polar and azimuthal angles
        for name, colIdx in zip(
            [ 'velTheta', 'velPhi' ],
            [ 1         , 2        ]
        ):
            for starIdx in [ 0, 1, 2 ]:
                key = f"{name}_({starIdx},0)"
                spcdot_i3[ starIdx, colIdx ] = sampleRow[ key ]

        # calculate XYZ velocities
        xdot_i3 = fun.spc2xyz( spcdot_i3 )

        # find star radii
        radii_i1 = fun.stellarRadiiLookup( m_i1 )

        # set starting run time and step counter
        steps, time = 0, 0

        # set terminition conditions
        collision = False
        ejection = False
        timeLimit = False

        # initialize time and positions to be updated
        x_i3_t    = deepcopy( x_i3 )
        xdot_i3_t = deepcopy( xdot_i3 )

        # initialize time step using smallest allowed radius & initial velocity
        dt = fun.timeStep( radiusParams[0], xdot_i3 )

        # run through simulation until any terminition conditions are met
        while all([ collision, ejection, timeLimit ]):

            # find change in velocity
            dv_i3 = fun.RungeKutta4(
                fun.nBodyAcceleration, # function to integrate
                dt, # time step to use
                x_i3_t, # current position
                m_i1, # other arguments for function ( mass )
            )

            # update velocity
            xdot_i3_t += dv_i3

            # find the change in position
            dx_i3 = xdot_i3_t * dt

            # update positions
            x_i3_t += dx_i3

            # update time
            t += dt

            # see if any stars collided
            collision = fun.checkCollision( x_i3_t )

            # see if any stars are moving to fast
            ejection = fun.checkEjection( xdot_i3_t, x_i3_t, m_i1 )

            # see if timit limit has been exceeded
            timeLimit = ( t >= maxT )

            # update time step
            dt = fun.timeStep( dx_i3, xdot_i3_t )

            # increment step counter
            steps += 1

        # convert ending values back to SPC
        spc_i3_t    = fun.xyz2spc( x_i3_t )
        spcdot_i3_t = fun.xyz2spc( xdot_i3_t )

        # create empty container to hold scenario results
        results = {}

        # add the run time and misc columns
        results['runTime']   = t
        results['treatment'] = self.sampleRowIdx_
        results['replicate'] = self.replicateCounter_
        results['steps']     = steps
        if collision:
            results['outcome'] = 'collision'
        elif ejection:
            results['outcome'] = 'ejection'
        else:
            results['outcome'] = 'fullRun'

        # add all positions, velocities and mass for each star
        for starIdx in [ 0, 1, 2 ]:

            # add mass to results
            results[ f"mass_({starIdx})" ] = m_i1[ starIdx, 0 ]

            # add initial positions (SPC)
            for colIdx, name in enumerate([ 'radius', 'theta', 'phi' ]):
                results[ f"{name}_({starIdx},0)" ] = spc_i3[ starIdx, colIdx ]

            # add final positions( (SPC)
            for colIdx, name in enumerate([ 'radius', 'theta', 'phi' ]):
                results[ f"{name}_({starIdx},-1)" ] = spc_i3_t[ starIdx, colIdx ]

            # add initial velocities (SPC)
            for colIdx, name in enumerate([ 'velRadial', 'velPolar', 'velAzimuthal' ]):
                results[ f"{name}_({starIdx},0)" ] = spcdot_i3[ starIdx, colIdx ]

            # add final velocities (SPC)
            for colIdx, name in enumerate([ 'velRadial', 'velPolar', 'velAzimuthal' ]):
                results[ f"{name}_({starIdx},-1)" ] = spcdot_i3_t[ starIdx, colIdx ]

        # add the senario data to data_
        row = pd.DataFrame( results, index=[0] )
        self.data_ = self.data_.append( row )

        # end

    #===========================================================================#
    # semi-private                                                              #
    #===========================================================================#

#===============================================================================#
# main                                                                          #
#===============================================================================#

if __name__ == "__main__":
    sim = Simulation()
    sim.run()
