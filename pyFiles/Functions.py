def generic():
    """
    use:

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
    pass

#===============================================================================#
# import internal dependencies                                                  #
#===============================================================================#

from Input import G, speedParams, thetaParams, phiParams

#===============================================================================#
# import external dependencies                                                  #
#===============================================================================#

import matplotlib.pyplot as plt
import numpy as np
import os
import pickle
import warnings

#===============================================================================#
# auxillary                                                                     #
#===============================================================================#

def findIdx( value, array ):
    """
    use:

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
    idx = np.abs( array - value ).argmin()
    return idx

#===============================================================================#
# coordinate frames                                                             #
#===============================================================================#

def findCM( x_i3, m_i1, **kwargs ):
    """
    use:

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
    CM = ( m_i1 * x_i3 ).sum( axis=0 ) / m_i1.sum()
    return CM[None,:]

def spc2xyz( spc_i3, **kwargs ):

    r = spc[:,0]

    sinTheta = np.sin( spc[:,1] )
    cosTheta = np.cos( spc[:,1] )

    sinPhi = np.sin( spc[:,2] )
    cosPhi = np.cos( spc[:,2] )

    xyz = np.zeros( *spc.shape )

    xyz[:,0] = r * sinTheta * cosPhi
    xyz[:,1] = r * sinTheta * sinPhi
    xyz[:,2] = r * cosTheta

    return xyz

def xyz2spc( x_i3, **kwargs ):

    r   = np.sqrt( ( xyz**2 ).sum( axis=1 ) )
    rho = np.sqrt( ( xyz[:,:2]**2 ).sum( axis=1 ) )

    spc = np.zeros( *xyz.shape )

    spc[:,0] = r
    spc[:,1] = np.arctan( rho / xyz[:,2] )
    spc[:,2] = np.arctan( xyz[:,1] / xyz[:,0] )

    return spc

#===============================================================================#
# file handling                                                                 #
#===============================================================================#

def toPickle( toFile, fromObject, **kwargs ):
    """
    use:
    sends object (preferably dictionary) to pickle and saves at file name
    provided.
    https://pythonprogramming.net/python-pickle-module-save-objects-serialization/

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:
    toFile          str             file name to save at
    fromObject      dict            dictionary (or other object) to send to
                                    pickle.

    kwargs:         type:           description:
    verbose         bool            whether to print save message.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    None            None
    """

    toFile = f"../data/{toFile}.pkl"

    pickle.dump(
        fromObject,             # object to write
        open( toFile, "wb" )    # open file and write object to it in bytes
    )

    printHeader( f"\n\tsaved pickle to {toFile}", **kwargs )

def fromPickle( fromFile, **kwargs ):
    """
    use:
    loads object (preferably from dictionary) from file name provided. if not
    file found, returns empty dictionary.
    https://pythonprogramming.net/python-pickle-module-save-objects-serialization/

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:
    fromFile        str             file name to look for pickled object

    kwargs:         type:           description:
    verbose         bool            whether to print load message.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    toObject        dict (or other object)
    """

    fromFile = f"../data/{fromFile}.pkl"

    if os.path.isfile( fromFile ):
        toObject = pickle.load(
            open( fromFile, 'rb' ) # read the byte file
        )
    else:
        toObject = {}

    return toObject

def saveFigure( toFile, fig, **kwargs ):
    """
    use:
    save a figure, print save destination if verbose

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:
    toFile          str             file name to save figure
    fig             matplotlib.figure

    kwargs:         type:           description:
    verbose         bool            flag to print, default = False

    ============================================================================
    output:         type:
    ============================================================================
    None            None
    """
    toFile = f"../figures/{toFile}.pdf"
    fig.savefig( toFile )
    plt.close( fig )
    printHeader( f"\n\tsaved figure: {toFile}", **kwargs )

#===============================================================================#
# math & physics                                                                #
#===============================================================================#

def escapeSpeed( x_i3, m_i1 ):

    warnings.filterwarnings("ignore", message="divide by zero encountered in true_divide" )
  # alpha = m_i1 / x_ij + m_i1.T / x_ij")

    # find the pair-wise difference vectors
    x_ij3 = pairwiseDifferenceVector( x_i3 )

    # find the pai-wise distances
    x_ij = pairwiseDistance( x_ij3 )

    # calculate intermidiary result
    alpha_ij = m_i1 / x_ij + m_i1.T / x_ij
    np.nan_to_num( alpha_ij, posinf=0, copy=False )

    # sum up all ( mass : distance ) contributions along axis = 1 = j,
    # "from body"
    alpha_i1 = alpha_ij.sum( axis=1 )[:,None]

    # calculate escape speed for all stars
    speed_i1 = np.sqrt( 2 * G * alpha_i1 )
    return speed_i1

def nBodyAcceleration( x_i3, m_i1 ):
    """
    ( i , j , 3 )
    i --> on body
    j --> from body
    3 --> xyz spatial vector
    """

    # find pair-wise difference vectors
    x_ij3 = pairwiseDifferenceVector( x_i3, **kwargs )

    # find pair-wise distances
    x_ij = pairwiseDistance( x_ij3 )

    # find pair-wise force directions
    hat_ij3 = x_ij3 / x_ij[:,:,None]
    np.nan_to_num( hat_ij3, copy=False )

    # find pair-wise mass product
    m_ij = m_i1 * m_i1[:,0]

    # find piece-wise force of gravity
    f_ij3 = hat_ij3 * G * m_ij[:,:,None] / x_ij[:,:,None]

    # sum up forces along ( 1 - from body ) to get forces on bodies
    f_i3 = f_ij3.sum( axis=1 )

    # get acellerations on bodies
    a_i3 = f_i3 / m_i1
    return a_i3

def pairwiseDifferenceVector( x_i3, **kwargs ):
    x_ij3 = x_i3 - x_i3[:,None,:]
    return x_ij3

def pairwiseDistance( x_ij3, **kwargs ):
    x_ij = np.sqrt( ( x_ij3**2 ).sum( axis=2 ) )
    return x_ij

def RungeKutta4( f, dt, x, *args ):

    k1  = f( x, *args )
    k23 = f( x + dt/2, *args )
    k4  = f( x + dt, *args )

    delta_y = dt * ( k1 + 2*k23 + 2*k23 + k4 ) / 6
    return delta_y

def timeStep( *args ):
    NotImplemented

#===============================================================================#
# printing                                                                      #
#===============================================================================#

def printBreak( **kwargs ):
    """
    use:
    prints a decorated break in terminal

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:

    kwargs:         type:           description:
    verbose         bool            whether to actually print or not.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    None            None
    """

    verbose = kwargs['verbose'] if 'verbose' in kwargs else False

    if verbose: print("\n\
        ========================================================================\
    ")

def printDict( dictionary, **kwargs ):
    """
    use:
    prints dictionary in a decorated and readable format

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:
    dictionary      dict            a dictionary to print

    kwargs:         type:           description:
    message         str             message to print in header, default =
                                    "dictionary"
    verbose         bool            whether to actually print or not.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    None            None
    """

    message = kwargs['message'] if 'message' in kwargs else "dictionary"
    verbose = kwargs['verbose'] if 'verbose' in kwargs else False

    if verbose:

        # package dictionary
        lines = [ "", f"{message}", "key:\tvalue", "=============" ]
        for key,value in dictionary.items():
            try:
                lines.append( f"{key}:\t{value:0.2f}" )
            except:
                lines.append( f"{key}:\t{value}" )
        printHeader( *lines, **kwargs )

def printHeader( *args, **kwargs ):
    """
    use:
    prints a decorated section header with any optional provided arguments
    printed on a new line.

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:
    line(s)         str             each provided argument gets printed in the
                                    header on a new line

    kwargs:         type:           description:
    verbose         bool            whether to actually print or not.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    None
    """

    verbose = kwargs['verbose'] if 'verbose' in kwargs else False

    if verbose:
        printBreak( **kwargs )
        for arg in args:
            try:
                print( f"\t{arg:0.2f}" )
            except:
                print( f"\t{arg}" )
        printBreak( **kwargs )

def printList( list1, **kwargs ):
    """
    use:

    ============================================================================
    input:          type:           description:
    ============================================================================
    args:           type:           description:

    kwargs:         type:           description:
    message         str             message to print in header, default =
                                    "List"
    verbose         bool            whether to actually print or not.
                                    default = False

    ============================================================================
    output:         type:
    ============================================================================
    None            None
    """

    message = kwargs['message'] if 'message' in kwargs else "List"
    verbose = kwargs['verbose'] if 'verbose' in kwargs else False

    if verbose:

        # package dictionary
        lines =  [ "", f"{message}", "=============" ]
        lines += list1
        printHeader( *lines, **kwargs )

#===============================================================================#
# random generator                                                              #
#===============================================================================#

def randomSpeed( maxSpeed_i1 ):

    # create empty array to hold random speed
    speed = np.zeros((
        maxSpeed_i1.shape[0], # number of bodies
        1,
    ))

    # fill in the random speeds
    for starIdx in range( maxSpeed_i1.shape[0] ):
        # create allowable speed args
        args = (
            speedParams[0], # min speed
            maxSpeed.item(), # the single value maxSpeed
            speedParams[1], # number of points
        )
        # create allowable speeds
        speeds = np.linspace( *args )
        # choose random speed index
        randIdx = np.random.randint( args[2] + 1 )
        # fill in random speed
        speed[ starIdx, 0 ] = speeds[ randIdx ]

    return speed
