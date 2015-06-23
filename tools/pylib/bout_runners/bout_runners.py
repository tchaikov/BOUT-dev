#!/usr/bin/env python


# NOTE: THE BOUT-RUNNERS ARE UNDER REVISION. THINGS MAY NOT WORK AS
# EXPECTED


"""Classes and functions for running several mpi-runs with BOUT++ at
   once. All post-processing are placed in own files.
   Run demo() for instructions."""
from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import range
from builtins import object

# NOTE: This document uses folding. A hash-symbol followed by three {'s
# denotes the start of a fold, and a hash-symbol followed by three }'s
# denotes the end of a fold
__authors__ = 'Michael Loeiten'
__email__   = 'mmag@fysik.dtu.dk'
__version__ = '0.8beta'
__date__    = '16.06.2015'

import textwrap
import os
import re
import itertools
import glob
import timeit
import datetime
import math
import six
from numpy import logspace
from numbers import Number
import numpy as np
from subprocess import check_output
from boututils import shell, launch, getmpirun
from boututils.datafile import DataFile
try:
    from bout_runners.bout_plotters import convergence_plotter,\
                                           solution_plotter,\
                                           solution_and_error_plotter
    from bout_runners.common_bout_functions import create_folder,\
                                                   find_variable_in_BOUT_inp,\
                                                   warning_printer,\
                                                   check_for_plotters_errors,\
                                                   clean_up_runs,\
                                                   message_chunker
except ImportError:
    print("Could not load bout_runners from the current directory")

# FIXME: qsub does not always delete the clean-up files??
#        Fixed for basic qsub (test it), fix for the rest
# TODO: Add grid functionality
# TODO: Clean up the mess in basic_error_checker
# TODO: Make it possible to give a function to the waiting routine in
#       qsub runners, so that it is possible to give a function which
#       will be run when a job has completed
# TODO: Make qsub usable on different clusters (and update documentation)
#       Can be done by checking the current cluster? (Need to set the
#       path to the correct libraries, and use the correct MPI runner)
# TODO: Submit and postprocess to a different queue
# TODO: Check if it is possible to use qsub with dependencies (only
#       found depricated documentation)
# TODO: 2-D solution and error plot (rewrite then the documentation in
#       plot_direction)
# TODO: Distinguish between 'spatial' and 'temporal' convergence run in
#       the log-file
# TODO: Make a flag, so that it is also possible to copy the .cxx file
#       to the simulation folder
# TODO: When doing a convergence run: Let nx, ny and MZ be set
#       independently (as shown in Salari and Knupp)

# TODO: Rewrite demo to new changes...rather make an example in BOUT++
#       examples. Different folders doing different things
# TODO: Do not set the memberdata, but use the constructor instead
#{{{demo
def demo(argument = None, plot_type = False, convergence_type = False):
    """This function is meant as a documentation of the bout-runners.
    It has two main purposes:
    1. To create text-string which can be used to make drivers.
    2. To explain the member data of the different classes."""

    # Generate text wrappers
    normal_text_wrapper = textwrap.TextWrapper(initial_indent='\n',\
                                               width = 80)
    lists_text_wrapper= textwrap.TextWrapper(initial_indent='',\
                                             subsequent_indent=' '*4,\
                                             width = 80)
    double_lists_text_wrapper= textwrap.TextWrapper(initial_indent=' '*4,\
                                             subsequent_indent=' '*8,\
                                             width = 80)

#{{{ Lists of argument and kwargs possibilities
    possible_classes = [\
        'basic_runner',\
        'run_with_plots',\
        'basic_qsub_runner',\
        'qsub_run_with_plots']

    possible_basic_runner_member_data = [\
        'solver',\
        'nproc',\
        'methods',\
        'n_points',\
        'directory',\
        'nout',\
        'timestep',\
        'MXG',\
        'MYG',\
        'additional',\
        'restart']

    possible_run_with_plots_member_data = [\
        'plot_type',\
        'extension']

    possible_basic_qsub_runner_member_data = [\
        'nodes',\
        'ppn',\
        'walltime',\
        'mail',\
        'queue']

    possible_plot_types = [\
        'solution_plot',\
        'solution_and_error_plot',\
        'convergence_plot']

    possible_sol_plotter_kwargs = [\
        'plot_direction',\
        'plot_times',\
        'number_of_overplots',\
        'collect_x_ghost_points',\
        'collect_y_ghost_points',\
        'show_plots']

    possible_conv_plotter_kwargs = [\
        'convergence_type',\
        'collect_x_ghost_points',\
        'collect_y_ghost_points',\
        'show_plots']

    possible_conv_type_kwargs = [\
        'spatial',\
        'temporal'
        ]
#}}}

##{{{ get_list_of_possibilities
    def get_list_of_possibilities():
        """Returns 'messages', a list of all possibility arguments for demo()"""
        # Appendable list
        messages = []
        messages.append("\nInfo about the demo function:")
        messages.append("    None")
        messages.append("\n")

        messages.append( "\nExample drivers:")
        for arg in possible_classes:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        messages.append( "\nUsage of 'basic_runner' member data:")
        for arg in possible_basic_runner_member_data:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        messages.append( "\nUsage of 'run_with_plots' member data:")
        for arg in possible_run_with_plots_member_data:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        messages.append( "\nUsage of 'basic_qsub_runner' member data:")
        for arg in possible_basic_qsub_runner_member_data:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        messages.append( "\nUsage of addition keyword arguments"+\
                        " in 'solution_plot' and"+\
                        " 'solution_and_error_plot':")
        for arg in possible_sol_plotter_kwargs:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        messages.append( "\nUsage of addition keyword arguments in "+\
                        " 'convergence_plot':")
        for arg in possible_conv_plotter_kwargs:
            messages.append( "    '" + arg + "'")
        messages.append("\n")

        return messages
#}}}

#{{{The basic info
    if argument == None:
        # Some whitespace
        print('\n'*2)
        # Appendable list
        messages = []
        messages.append("Welcome to the 'demo' of 'bout_runners'")
        messages.append("Use one of the following arguments in the demo()"+\
                        " function in order to get info about:\n")
        for message in messages:
            print(normal_text_wrapper.fill(message))

        # Get the possibilities
        messages=get_list_of_possibilities()
        for message in messages:
            print(lists_text_wrapper.fill(message))
        # Some whitespace
        print('\n'*2)

        # Appendable list
        messages = []
        # Writing the basic info
        messages.append("BASIC INFO")
        messages.append("==========")
        messages.append("The purpose of bout_runners is to run several runs"+\
                        " of a BOUT++ program with different options for"+\
                        " each run. Each run is run from the shell with"+\
                        " command line options.")
        messages.append("In this way, one can use a single BOUT.inp file as"+\
                        " a template. Options given by the user (which"+\
                        " differs from  what is written in this template)"+\
                        " are called with additional command line arguments"+\
                        " for the specific run in the shell.")
        messages.append("A log folder for the runs are made (and eventually"+\
                        " appended) in the folder of the template BOUT.inp"+\
                        " file.")
        messages.append("The parent class in 'bout_runners' is"+\
                        " 'basic_runner'. All classes derives from this"+\
                        " file. 'basic_runner' creates a folder"+\
                        " structure for each run, and subsequently runs"+\
                        " the runs through the shell. For more information,"+\
                        " see the documentation of 'basic_runner'.")
        messages.append("The class 'run_with_plots' are made compatible with"+\
                        " the classes found in 'bout_plotters', so that"+\
                        " plots can be performed directly after runs. If"+\
                        " the user wants more plot types than written,"+\
                        " the plot type can easily be introduced by writing"+\
                        " a child class in 'bout_plotters'. For more"+\
                        " information, see the documentation of"+\
                        " 'bout_plotters'.")
        messages.append("The 'qsub'-classes in this file gives the"+\
                        " possibility to run the runs on a torque cluster."+\
                        " Both the different runs and the post processing are"+\
                        " submitted as jobs to the cluster. For more"+\
                        " information see the documentation of"+\
                        " 'basic_qsub_runner' or 'qsub_run_with_plots'")
        messages.append("All the classes and functions are equipped with so"+\
                        " called 'docstrings', which explains the purpose of"+\
                        " the class/function. The docstring can be read in")
        for message in messages:
            print(normal_text_wrapper.fill(message))

        messages = []
        messages.append("1) The source code")
        messages.append("2) By importing the function/class in an"+\
                        " interpreter and")
        for message in messages:
            print(lists_text_wrapper.fill(message))

        messages = []
        messages.append("a) type class_or_function_name.__doc__ or")
        messages.append("b) type help(class_or_function-name)")
        for message in messages:
            print(double_lists_text_wrapper.fill(message))

        print('\n')
        messages = []
        messages.append("THE DEMO FUNCTION")
        messages.append("=================")
        messages.append("The idea behind the demo function is to explain"+\
                        " a simple way thath one can use the 'bout_runners'"+\
                        " classes in.")
        messages.append("It is recommended to use the classes through"+\
                        " 'drivers'. A 'driver' is here referred to a python"+\
                        " script which executes all necessary functions."+\
                        " Examples of such scripts can be obtained by"+\
                        " running demo('class'), where 'class' is the"+\
                        " name of the desired class.")
        messages.append("If you find any bugs, or have any suggestions on to"+\
                        " improve the classes, do not hesitate to contact the"+\
                        " author")
        for message in messages:
            print(normal_text_wrapper.fill(message))

        return
#}}}

#{{{ Lists of argument and kwargs possibilities
    possible_classes = [\
        'basic_runner',\
        'run_with_plots',\
        'basic_qsub_runner',\
        'qsub_run_with_plots']

    possible_basic_runner_member_data = [\
        'solver',\
        'nproc',\
        'methods',\
        'n_points',\
        'directory',\
        'nout',\
        'timestep',\
        'MXG',\
        'MYG',\
        'additional',\
        'restart']

    possible_run_with_plots_member_data = [\
        'plot_type',\
        'extension']

    possible_basic_qsub_runner_member_data = [\
        'nodes',\
        'ppn',\
        'walltime',\
        'mail',\
        'queue']

    possible_plot_types = [\
        'solution_plot',\
        'solution_and_error_plot',\
        'convergence_plot']

    possible_sol_plotter_kwargs = [\
        'plot_direction',\
        'plot_times',\
        'number_of_overplots',\
        'collect_x_ghost_points',\
        'collect_y_ghost_points',\
        'show_plots']

    possible_conv_plotter_kwargs = [\
        'convergence_type',\
        'collect_x_ghost_points',\
        'collect_y_ghost_points',\
        'show_plots']

    possible_conv_type_kwargs = [\
        'spatial',\
        'temporal'
        ]
#}}}

    if (argument in possible_classes) == False\
        and (argument in possible_basic_runner_member_data) == False\
        and (argument in possible_run_with_plots_member_data) == False\
        and (argument in possible_basic_qsub_runner_member_data) == False\
        and (argument in possible_sol_plotter_kwargs) == False\
        and (argument in possible_conv_plotter_kwargs) == False:

        messages=get_list_of_possibilities()
        # Cast the list to a string in order to be able to print it in
        # the TypeError
        message = "\n".join(messages)
        message = message.replace('\n\n\n\n','\n\n')
        self.errors.append("TypeError")
        raise TypeError (message)

    elif (argument in possible_classes):
#{{{ Print the demo script
        # If we want the information of any of the plot classes, we must
        # make sure that the plot_type is given
        if 'plot' in argument:
            if (plot_type in possible_plot_types) == False:
                message = "'plot_type' must be given when using '"+\
                          argument + "' as an argument\n"
                message += "Possible 'plot_types' are:\n"
                for arg in possible_plot_types:
                    message += "    '" + arg + "'\n"
                self.errors.append("TypeError")
                raise TypeError (message)

            # If plot_type is set to convergence plot, we must know what
            # convergence_type we must use
            elif plot_type == 'convergence_plot' and\
                 (convergence_type in possible_conv_type_kwargs)== False:
                message = "'convergence_type' must be given when using '"+\
                          plot_type + "' as an argument\n"
                message += "Possible 'convergence_types' are:\n"
                for arg in possible_conv_type_kwargs:
                    message += "    '" + arg + "'\n"
                self.errors.append("TypeError")
                raise TypeError (message)

        # Writing the driver
        # Making a header
        message = argument.upper()
        header_length = len(message)
        message += "\n"*2
        message += "="*header_length
        message += "\n"*2
        message += "#!/usr/bin/env python\n"
        # The root of the example folder
        example_folder = "# 'BOUT/examples/"

        # Additional plot_type arguments
        if plot_type != False:
            message += '# NOTE: Ghost points will be collected for x '\
                       'if kwarg collect_y_ghost_points = True)\n'
            if plot_type == 'solution_and_error_plot' or\
               plot_type == 'convergence_plot':
                message += "\n# NOTE: For these to run properly, we need to"+\
                           " set 'mms=true' in the BOUT.inp file.\n"
                message += "#       Also, make sure you are familiar with"+\
                           " how to use mms. See f.ex. Salari and Knupp\n"+\
                           "#       'Code Verification by the Method of"+\
                           "Manufactured Solutions' (especially 5 Step 2"+\
                           " and appendix C)\n"
                if plot_type == 'convergence_runner':
                    message += "#       This run is not meant as a "+\
                               "convergence test, but rather as a "+\
                               "demonstration of bout_runners"
        # Additional qsub arguments
        if 'qsub' in argument:
            message += "# NOTE: qsub is for now only tested on a torque cluster.\n"
            message += "# Other clusters might have different syntax.\n"
            message += "# If you want to use a different cluster, please"+\
                       " contact the author.\n"
        # Finishing the header
        message += "# Example of a driver for '" + argument + "'\n"
        message += "# Some of the member data we set in this example are"+\
                   " superfluous in order to show\n"
        message += "# 'bout_runners' flexibility.\n"
        message += "# Save the following as for example 'driver.py'"+\
                   ", put the file in for example \n"
        if argument == 'basic_runner' or argument == 'basic_qsub_runner':
            example_folder += "test-wave'\n"
            message += example_folder
        elif argument == 'run_with_plots' or\
            argument == 'qsub_run_with_plots':
            if plot_type == 'solution_and_error_plot' or\
               (plot_type == 'convergence_plot' and\
               convergence_type == 'spatial'):
                example_folder += "mms/diffusion2'\n"
                message += example_folder
            elif convergence_type == 'temporal':
                example_folder += "mms/time'\n"
                message += example_folder
            elif plot_type == 'solution_plot':
                example_folder += "test-wave'\n"
                message += example_folder
        message += "# and execute the script\n\n"

        # Start the bulk of the script
        message += "from bout_runners.bout_runners import " + argument + "\n"
        message += "from numpy import logspace\n\n"
        # Make the folders
        message += "folders = ["
        if 'test-wave' in example_folder or 'time' in example_folder:
            message += "'data']\n\n"
        elif 'diffusion' in example_folder:
            message += "'X', 'Y']\n\n"
        message += "# We want the following spacing of our grid\n"
        message += "spacing = logspace(3,6,4,base=2)\n"
        # Setting the spacing
        if convergence_type == 'temporal':
            message += "# Make the timestep successively smaller\n"
            message += "spacing = [1.0/float(n) for n in spacing]\n"
        else:
            message += "# Convert the spacing to integers\n"
            message += "spacing = [int(n) for n in spacing]\n"
        # Setting the variables if plot_type is not false
        if plot_type != False:
            message += "variables = ['"
            if 'test-wave' in example_folder:
                message += "f', 'g', 'f2', 'g2']\n"
            elif 'diffusion' in example_folder:
                message += "N']\n"
            elif 'time' in example_folder:
                message += "f']\n"
            if plot_type == 'solution_plot' or\
               plot_type == 'solution_and_error_plot':
                if 'test-wave' in example_folder:
                    # For example_folder == 'diffusion2', see below
                    message += "plot_direction = {'x':2, 'y':'all', 'z':0}\n"
                message += "number_of_overplots = 4\n"
                message += "# plot_times have precedence over"+\
                           " number_of_overplots\n"
                message += "#plot_times = [0.1, 0.3, 1]\n"
            elif plot_type == 'convergence_plot':
                message += "convergence_type = '" + convergence_type + "'\n"
        message += "\n\n"
        message += "# Loop over all desired folders\n"
        message += "for folder in folders:\n"
        message += "    # All the member data can in principle be set by"+\
                   " the constructor.\n"
        message += "    # However, for clarity we set the member data "+\
                   " here individually.\n"
        message += "    my_class_instance = " + argument  + "("
        if argument == 'run_with_plots' or argument == 'qsub_run_with_plots':
            message += "'" + plot_type + "'"
        message += ")\n"
        # Setting the solver
        my_solver = "    my_class_instance.solver = "
        if 'time' in example_folder:
            message += my_solver + "['euler', 'karniadakis', 'rk3ssp', 'rk4']\n"
        else:
            message += my_solver + "['pvode', 'rk4']\n"
        # Setting the number of processors
        message += "    my_class_instance.nproc = 4\n"
        # Setting the method
        my_method = "    my_class_instance.methods = "
        if 'test-wave' in example_folder:
            message += my_method + "{'ddy':{'second':['C2']}}\n"
        elif 'diffusion2' in example_folder:
            message += "    # We must manually set the name of the"+\
                       " program file, as it differs from the .cxx name\n"
            message += "    my_class_instance.program_name = 'cyto'\n"
            message += "    # diffusion2 only contains 'second' terms.\n"
            message += "    # Setting 'upwind' terms will therefore have"+\
                       " no effect on the runs.\n"
            message += "    # It is however included here to show the"+\
                       " resulting folder structure.\n"
            message += my_method +\
                       "{'ddx':{'upwind':['U1', 'W3'], 'second':['C2']},"+\
                       " 'ddy':{'upwind':['U1']}}\n"
        # Setting the n_points
        my_grid = "    my_class_instance.n_points = "
        if 'test-wave' in example_folder:
            message += my_grid + "{'mesh:ny':spacing}\n"
        elif 'diffusion2' in example_folder:
            if plot_type == 'solution_and_error_plot':
                message += "    # Looping over MZ as done here is not"+\
                           " necessare, but is here done to illustrate"+\
                           " the resulting combination of runs\n"
                message += "    if folder == 'X':\n"
                message += " "*4 + my_grid +\
                           "{'mesh:nx':spacing, 'mesh:ny':[8],"+\
                           " 'MZ':[space + 1 for space in spacing if"+\
                           " space%32==0]}\n"
                message += "    else:\n"
                message += " "*4 + my_grid +\
                           "{'mesh:nx':[8], 'mesh:ny':spacing,"+\
                           " 'MZ':[space + 1 for space in spacing if"+\
                           " space%32==0]}\n"
            elif plot_type == 'convergence_plot':
                message += my_grid + "{'mesh:nx':spacing, 'mesh:ny':spacing,"+\
                           " 'MZ':[space + 1 for space in spacing]}\n"
        elif 'time' in example_folder:
            message += my_grid + "{'mesh:ny':[4], 'mesh:nx':[4], 'MZ':[5]}\n"
        message += "    my_class_instance.directory = folder\n"
        message += "    my_class_instance.nout = 10\n"
        # Setting the timestep
        my_timestep = "    my_class_instance.timestep = "
        if 'time' in example_folder:
            message += my_timestep + "spacing\n"
        else:
            message += my_timestep + "[0.1]\n"
        # Set guard cells
        if ('time' in example_folder) == False:
            message += "    my_class_instance.MXG = 1\n"
            message += "    my_class_instance.MYG = 1\n"
        message += "    # The member data 'additional' is in this example"+\
                   " without any effect on the runs.\n"
        message += "    # However, if the BOUT.inp file would have contained"+\
                   " the variables 'heatflux' and\n"
        message += "    # 'viscosity' under the section [fluid].\n"
        message += "    # Uncomment to see the resulting folder structure.\n"
        message += "    # my_class_instance.additional ="+\
                   " {'level':2, 'name':False,"+\
                   " 'value':{'fluid:heat_flux':[2,3],"+\
                   " 'fluid:viscosity':[1,2,3]}}\n"
        message += "    my_class_instance.restart = False\n"

        if (plot_type == 'solution_plot' or\
           plot_type == 'solution_and_error_plot') and\
           'diffusion2' in example_folder:
            # If example_folder == 'test-wave', see above
                message += "    if folder == 'X':\n"
                message += "        plot_direction = {'x':'all', 'y':0, 'z':0}\n"
                message += "    else:\n"
                message += "        plot_direction = {'x':0, 'y':'all', 'z':0}\n"
        if 'qsub' in argument:
            message += "    my_class_instance.nodes = '1'\n"
            message += "    my_class_instance.ppn = '4'\n"
            message += "    my_class_instance.walltime = '00:20:00'\n"
            message += "    my_class_instance.mail = False\n"
            message += "    my_class_instance.queue = False\n"
        my_runner = "    my_class_instance.run"
        # How to run the run function
        if argument == 'basic_runner' or argument == 'basic_qsub_runner':
            message += "    # remove_old is set to False by default.\n"
            message += "    # If there are no previous files, an ignorable error"+\
                   " message is displayed.\n"
            message += my_runner + "(remove_old = True)\n"
        elif 'plot' in argument:
            my_runner += "(variables = variables, show_plots = False, "+\
                         "collect_x_ghost_points = False, "+\
                         "collect_y_ghost_points = False, "
            if plot_type == 'solution_plot' or\
               plot_type =='solution_and_error_plot':
                message += my_runner + "plot_direction = plot_direction,"+\
                           " number_of_overplots = number_of_overplots)\n"
            elif plot_type == 'convergence_plot':
                message += my_runner + "convergence_type = convergence_type)\n"

        # Print the message without any wrapper
        print(message)
#}}}

    else:
#{{{Print the member data info
        # Empty list
        messages = []
        messages.append(argument.upper())
        messages.append("="*len(argument))
        if argument in possible_basic_runner_member_data:
            if argument == 'solver':
                messages.append("Must be given as a list of strings.")
                messages.append(" Available solver are found in the"+\
                                " BOUT++ manual.")
            elif argument == 'nproc':
                messages.append("Must be given as a number. Determines"+\
                                " the number in")
                messages.append("mpirun -np=number ...")
            elif argument == 'methods':
                messages.append("Must be given as a dictionary.")
                messages.append("The keys of the dictionary must be"+\
                                " either 'ddx', 'ddy' or 'ddz'.")
                messages.append("The values of the keys must again be"+\
                                " dictionaries. In the top level dictionary"+\
                                " the keys must be one of the differencing"+\
                                " methods (f.ex. 'first', 'upwind' etc.)."+\
                                " The values of the top level"+\
                                " dictionary must be a list of the methods"+\
                                " (f.ex. 'C2', 'W3' etc.")
            elif argument == 'n_points':
                messages.append("Must be given as a dictionary.")
                messages.append("The keys of the dictionary must be"+\
                                " either 'mesh:nx', 'mesh:ny' or 'MZ'.")
                messages.append("The values of the keys must be"+\
                                " a list of number representing the"+\
                                " number of points in the grid.")
                messages.append("Note that these numbers can be altered"+\
                                " by 'convergence_plot' in order to"+\
                                " get equal grid size in all directions.")
            elif argument == 'directory':
                messages.append("Must be given as a string.")
                messages.append("Relative path to the location of the"+\
                                " BOUT.inp template.")
            elif argument == 'nout':
                messages.append("Must be given as a number.")
                messages.append("Number of outputs in the output files.")
            elif argument == 'timestep':
                messages.append("Must be given as a list of numbers.")
                messages.append("Gives the initial step for the adaptive"+\
                                " solver, and the absolute timestep for"+\
                                " the non-adaptive time solver.")
            elif argument == 'MXG':
                messages.append("Must be given as a numbers.")
                messages.append("Number of guard cells in the x-direction.")
            elif argument == 'MYG':
                messages.append("Must be given as a numbers.")
                messages.append("Number of guard cells in the y-direction.")
            elif argument == 'additional':
                messages.append("Must be given as a dictionary.")
                messages.append("The idea behind this keyword is to add"+\
                                " additional keywords to the command line"+\
                                " of a run.")
                messages.append("The keys must be set to 'level', 'name'"+\
                                " and 'value'.")
                messages.append("If 'level':0  => 'name' must be set to"+\
                                " the name of the command-line variable,"+\
                                " and 'value' must be a number.")
                messages.append("If 'level':1  => 'name' must be set to"+\
                                " the name of the command-line variable,"+\
                                " and 'value' must be a list.")
                messages.append("If 'level':2  => 'value' must be a"+\
                                " dictionary. This is useful if the user"+\
                                " wants to specify a variable of one of"+\
                                " the sections in BOUT.inp")
                messages.append("If 'level':3  => 'value' must be a"+\
                                " dictionary with dictionaries as"+\
                                " values.")
            elif argument == 'restart':
                messages.append("Must be given as a string.")
                messages.append("If set, the run will start from the"+\
                                " last output.")
                messages.append("Can be set to 'overwrite' (new outputs"+\
                                " will override previous) or 'append'"+\
                                " (new outputs will be appended).")

        # Get info about run_with_plots member data
        elif argument in possible_run_with_plots_member_data:
            messages.append("Used in 'run_with_plots',"+\
                            " 'run_with_plots' and 'qsub_run_with_plots'.")
            if argument == 'plot_type':
                messages.append("Sets the type of plot.")
                messages.append("Possible plots types are 'solution_plot',"+\
                                " 'solution_and_error_plot' and"+\
                                " 'convergence_plot'")
                messages.append("Additional plot types can be made by"+\
                                " making child functions in the file"+\
                                " 'bout_plotters.py'. For more"+\
                                " information, see the documentation of"+\
                                " 'bout_plotters.py'")
            elif argument == 'extension':
                messages.append("Sets the file extension of the saved"+\
                                " plot.")
                messages.append("Set to 'png' by default.")

        # Get info about basic_qsub_runner member data
        elif argument in possible_basic_qsub_runner_member_data:
            messages.append("Used in 'basic_qsub_runner' and"+\
                            " 'qsub_run_with_plots'.")
            if argument == 'nodes':
                messages.append("Number of nodes one job will use on the"+\
                                " cluster.")
            elif argument == 'ppn':
                messages.append("Processors per node to be used by one job.")
            elif argument == 'walltime':
                messages.append("Maximum allowed time for one job on the"+\
                                " cluster.")
                messages.append("Must be given as a string on the form"+\
                                " HH:MM:SS.")
            elif argument == 'mail':
                messages.append("Specify your e-mail address if you want"+\
                                " the torque system when a job has finished.")
            elif argument == 'queue':
                messages.append("Specify the queue system to submit the"+\
                                " job to.")

        # Get info about possible_sol_plotter_kwargs arguments
        elif argument in possible_sol_plotter_kwargs:
            messages.append("Additional keyword used in "+\
                            " 'solution_plot' and "+\
                            " 'solution_and_error_plot'.")
            if argument == 'plot_direction':
                messages.append("Determines the slicing of the plot.")
                messages.append("Must be specified as a dictionary,"+\
                                " where the keys are 'x', 'y' and 'z'."+\
                                " Each direction can be set to a number"+\
                                " in the grid, or to 'all'. Note that"+\
                                " at least one direction must be set to"+\
                                " 'all', but no more than two (as 2-D"+\
                                " plots are not implimented yet).")
            elif argument == 'plot_times':
                messages.append("Must be given as a list of numbers.")
                messages.append("The plotter makes one over plot for the"+\
                                " each of the given times in the list for"+\
                                " 1D plots.")
            elif argument == 'number_of_overplots':
                messages.append("Must be given as an integer.")
                messages.append("Makes an over plot of the solution at"+\
                                " equally distanced time in 1D plots."+\
                                " 'plot_times' has precedence over"+\
                                " 'number_of_overplots'.")
            elif argument == 'collect_x_ghost_points':
                messages.append("Toggle collection of x ghost points.")
            elif argument == 'collect_y_ghost_points':
                messages.append("Toggle collection of y ghost points.")
            elif argument == 'show_plots':
                messages.append("Toggle whether plots will be shown or not.")
                messages.append("Can be set to 'True' or 'False' (default).")

        # Get info about conv_plotter_kwargs arguments
        elif argument in possible_conv_plotter_kwargs:
            messages.append("Additional keyword used in"+\
                            " 'convergence_plot'.")
            if argument == 'convergence_type':
                messages.append("Must be given as a string.")
                messages.append("Can be set to either 'spatial' or"+\
                                " 'temporal'.")
            elif argument == 'show_plots':
                messages.append("Toggle whether plots will be shown or not.")
                messages.append("Can be set to 'True' or 'False' (default).")

        for message in messages:
            print(normal_text_wrapper.fill(message))
        print('\n'*2)
#}}}
#}}}



# FIXME: Idea: Dimension given as a tuple (nx, ny, nz)
#              Can read dimension from grid file
#              If not found in grid file, read from BOUT.inp
#              grid file has higher preceedence than BOUT.inp


#{{{class basic_runner
# As an inherit class uses the super function, the class must allow an
# object as input
class basic_runner(object):
# TODO: Edit here how it is going to be
# TODO: Tell that self.nx, self.ny and self.nz can be set by the grid
#       file
#{{{docstring
    """Class for mpi running one or several runs with BOUT++.
    Calling self.run() will run your BOUT++ program with all possible
    combinations given in the member data using the mpi runner.

    Before each run, a folder system, based on the member data, rooted
    in self.directory, will be created. The BOUT.inp of self.directory
    is then copied to the execution folder.

    A log-file for the run is stored in self.directory

    By default self.directory = 'data' and self.nproc = 1.

    self.program_name is by default set to the same name as any .o files in the
    folder where an instance of the object is created. If none is found
    the creator tries to run make. If no .o files are found then,
    self.program_name is set to False.

    All other data members are set to False by default.

    The data members will override the corresponding options given in
    self.directory/BOUT.inp.

    Run demo() for examples."""
#}}}

# The constructor
#{{{__init__
    def __init__(self,\
                 nproc      = 1,\
                 directory  = 'data',\
                 solver     = None,\
                 nx         = None,\
                 ny         = None,\
                 nz         = None,\
                 grid_file  = None,\
                 ddx_first  = None,\
                 ddx_second = None,\
                 ddx_upwind = None,\
                 ddx_flux   = None,\
                 ddy_first  = None,\
                 ddy_second = None,\
                 ddy_upwind = None,\
                 ddy_flux   = None,\
                 ddz_first  = None,\
                 ddz_second = None,\
                 ddz_upwind = None,\
                 ddz_flux   = None,\
                 nout       = None,\
                 timestep   = None,\
                 MXG        = None,\
                 MYG        = None,\
                 additional = None,\
                 restart    = None,\
                 cpy_source = None,\
                 allow_size_modification = False):
        """The constructor of the basic_runner"""

        # Setting the member data
        self.nproc      = nproc
        self.directory  = directory
        self.solver     = self.set_member_data(solver)
        self.nx         = self.set_member_data(nx)
        self.ny         = self.set_member_data(ny)
        self.nz         = self.set_member_data(nz)
        self.grid_file  = self.set_member_data(grid_file)
        self.ddx_first  = self.set_member_data(ddx_first)
        self.ddx_second = self.set_member_data(ddx_second)
        self.ddx_upwind = self.set_member_data(ddx_upwind)
        self.ddx_flux   = self.set_member_data(ddx_flux)
        self.ddy_first  = self.set_member_data(ddy_first)
        self.ddy_second = self.set_member_data(ddy_second)
        self.ddy_upwind = self.set_member_data(ddy_upwind)
        self.ddy_flux   = self.set_member_data(ddy_flux)
        self.ddz_first  = self.set_member_data(ddz_first)
        self.ddz_second = self.set_member_data(ddz_second)
        self.ddz_upwind = self.set_member_data(ddz_upwind)
        self.ddz_flux   = self.set_member_data(ddz_flux)
        self.nout       = self.set_member_data(nout)
        self.timestep   = self.set_member_data(timestep)
        self.MXG        = self.set_member_data(MXG)
        self.MYG        = self.set_member_data(MYG)
        self.additional = additional
        self.restart    = restart
        self.cpy_source = cpy_source
        self.allow_size_modification = allow_size_modification

        # self.additional must be on a special form (see
        # basic_error_checker).
        if self.additional != None:
            if not(hasattr(self.additional, "__iter__")) or\
               (type(self.additional) == str) or\
               (type(self.additional) == dict):
                # Put additional as a double iterable
                self.additional = [(self.additional)]
            else:
                if not(hasattr(self.additional[0], "__iter__")) or\
                   (type(self.additional[0]) == str) or\
                   (type(self.additional) == dict):
                    # Put self.additional as an iterable
                    self.additional = [self.additional]

        # Initializing self.warnings and self.error
        # self.warnings will be filled with warnings
        # self.errors will be filled with errors
        # The warnings and errors will be printed when the destructor is called
        self.warnings   = []
        self.errors     = []

        # Check if the program is made. Make it if it isn't
        # Find all files with the extension .o
        o_files = glob.glob("*.o")
        if len(o_files) > 0:
            # Pick the first instance as the name
            self.program_name = o_files[0].replace('.o', '')
        else:
            # Check if there exists a make
            make_file = glob.glob("*make*")
            if len(make_file) > 0:
                # Run make
                self.make()
                # Search for the .o file again
                o_files = glob.glob("*.o")
                if len(o_files) > 0:
                    self.program_name = o_files[0].replace('.o', '')
                else:
                    self.program_name = False
                    message = 'The constructor could not make your'+\
                              ' program'
                    self.warnings.append(message)
                    warning_printer(message)
            else:
                self.errors.append("RuntimeError")
                raise RuntimeError("No make file found in current" +\
                                   " directory")

        # Obtain the MPIRUN
        self.MPIRUN     = getmpirun()

        # Data members used internally in this class and its subclasses
        # The dmp_folder is the the folder where the runs are stored
        # It will be set by self.prepare_dmp_folder
        self.dmp_folder = None

        # The run type is going to be written in the run.log file
        self.run_type   = 'basic'

        # Counters
        # Number of runs per group
        # The runs are going to be divided into groups.
        # For example if we are doing a convergence plot:
        # One group equals one convergence plot
        # Usually a group only contains one run
        self.no_runs_in_group = False
        # Count number of runs in a group
        self.run_counter      = False
        # A group counter
        self.group_no = 0
        # Dictionary to be filled with the folders and the status of the
        # different runs in the  group
        self.run_groups = {}
        # The entries of dmp_folder are the paths where the dmp files
        # will be sotred. This makes our job easy when we want to make
        # a plot of grouped runs.
        # The entries in job_status will be filled with the job_name
        # If the job has already been done previously, the job status will
        # be set to 'done'.
        self.run_groups[self.group_no] ={'dmp_folder':[], 'job_status':[]}
#}}}

# The destructor
# TODO: Get the exit code of the process. If the process failed, write
#       that an error occured instead
#       Could eventually check if a error flag has been set to true
#{{{__del__
    def __del__(self):
        """The destructor will print all the warning and error messages"""

        # Switch to see if error occured
        error_occured = False

        # If errors occured
        if len(self.errors) > 0:
            message = "! A " + self.errors[0] + " occured. !"
            # Find the boarder length
            len_boarder = len(message)
            # Print the message
            print("\n"*2 + "!"*len_boarder)
            print(message)
            print('!'*len_boarder + "\n"*2)
            error_occured = True
        if len(self.warnings) > 0:
            print('\n'*3 + 'The following WARNINGS were detected:')
            print('-'*80)
            for warning in self.warnings:
                print(warning + '\n')
            print('\n'*3)
            print(' ' + '~'*69 + '\n'*3)
        elif len(self.warnings) > 0 and not(error_occured):
            print('\n'*3 + ' ' + '~'*69)
            print("| No WARNINGS detected before instance destruction in"+\
                  " 'bout_runners'. |")
#}}}

# The main function
# TODO: Edit here
#       Add nx, ny and nz
#       There will be no combination of of those
#       If the sizes are not the same a runtime error will be obtained
# TODO: Add the method to check if nx and ny is possible to split
# FIXME: n_points has been changed
# FIXME: methods has been changed
#{{{run
    def run(self, remove_old = False, **kwargs):
        """Makes a run for each of the combination given by the member
        data"""

        # TODO: Check if this is superfluous, as initialize run is doing
        #       the error checks
        # Check for errors
        self.error_checker(**kwargs)

        # Check for errors
        self.basic_error_check(remove_old)

        # Initialize the run by checking errors, and making the run_log
        self.create_run_log()

        # We check that the given combination of nx and ny is
        # possible to perform with the given nproc
        # FIXME: YOU ARE HERE
        #        SHOULD NOT BE POSSIBLE TO HAVE SEVERAL POSSIBILITIES OF
        #        MXG AND MYG
        if (self.nx != None) and (self.ny != None):
            self.get_correct_domain_split()

        # Get the combinations of the member functions
        import pdb
        pdb.set_trace()
        all_possibilities, spatial_grid_possibilities, timestep_possibilities =\
            self.get_possibilities()
        all_combinations = self.get_combinations(\
            all_possibilities, spatial_grid_possibilities, timestep_possibilities,\
            **kwargs)

        # Set the run_counter and the number of runs in one group
        self.set_run_counter(**kwargs)

        # The run
        self.print_run_or_submit()
        for run_no, combination in enumerate(all_combinations):

            # Get the folder to store the data
            self.prepare_dmp_folder(combination)

            if remove_old:
                # Remove old data
               self.remove_data()

            # Check if the run has been performed previously
            do_run = self.check_if_run_already_performed()
            # Do the actual runs
            self.run_driver(do_run, combination, run_no)

            # Append the current dump folder to the current run_group
            self.run_groups[self.group_no]['dmp_folder'].append(self.dmp_folder)
            # Update the run counter
            self.run_counter += 1

            # If we have looped over all the folders in a run
            # group, we will change the run group (as long as run_no is
            # lower than all_combinations [remember that run_no starts
            # from 0 and len() 'starts' from 1])

            if (self.run_counter % self.no_runs_in_group == 0)\
                and (run_no < len(all_combinations)-1):

                # Update the group number
                self.group_no += 1
                # Create a new key in the dictionary for the new
                # run group
                self.run_groups[self.group_no] =\
                    {'dmp_folder':[], 'job_status':[]}

        # post_run defines what to be done after the runs have finished/
        # been submitted (if anything)
        self.post_run(**kwargs)
#}}}

# The run_driver
#{{{run_driver
    def run_driver(self, do_run, combination, run_no):
        """The machinery which actually performs the run"""
        # Do the run
        if do_run:
            start = datetime.datetime.now()
            output, run_time = self.single_run( combination )
            # Print info to the log file for the runs
            self.append_run_log(start, run_no, run_time)
        print('\n')

        # As the jobs are being run in serial, the status of the job
        # will be done for all jobs
        self.run_groups[self.group_no]['job_status'].append('done')
#}}}

# Functions called directly by the main function
#{{{
#{{{print_run_or_submit
    def print_run_or_submit(self):
        """Prints 'Now running'"""
        print("\nNow running:")
#}}}

#{{{error_checker
    def error_checker(self, **kwargs):
        """Virtual function. Will in child classes check for additional
        errors"""
        return
#}}}

#{{{create_run_log
    def create_run_log(self):
        """Makes a run_log file if it doesn't exists"""

        # Checks if run_log exists
        self.run_log = self.directory + "/run_log.txt"
        if os.path.isfile(self.run_log) == False:
            # Create a file to be appended for each run
            f = open(self.run_log , "w")
            # The header
            header = ['start_time', 'run_type', 'run_no', 'dump_folder', 'run_time_H:M:S']
            header = '    '.join(header)
            f.write('#' + header + '\n')
            f.close()

            # Preparation of the run
            print("\nRunning with inputs from '" + self.directory + "'")
#}}}

#{{{get_possibilities
    def get_possibilities(self):
        """ Returns a list of list containing the possibilities from
        the changed data members"""

        # TODO: Ok, we need a clear idea of what is going to happen in
        #       this section. We can implement it as a list of
        #       list...in the end we can say that the possibilities are
        #       just an "addon" to the normal runner
        #       Thus, the easiest would be to run the bout runners
        #       without any looping, that would lead to the normal
        #       BOUT.inp file.
        #       The next step would be to change the grid size (this
        #       would be different than the time and nout)
        #       Finally, we can add the different combinations of the
        #       other input parameters



        # Set the combination of nx, ny and nz (if it is not already
        # given by the gridfile)
        if (self.grid_file == None):
            # Appendable lists
            spatial_grid_possibilities = []
            nx_str = []
            ny_str = []
            nz_str = []
            # Append the different dimension to the list of strings
            if self.nx != None:
                for nx in self.nx:
                    nx_str.append(' mesh:nx=' + str(nx))
            if self.ny != None:
                for ny in self.ny:
                    ny_str.append(' mesh:ny=' + str(ny))
            if self.nz != None:
                for nz in self.nz:
                    nz_str.append(' mesh:nz=' + str(nz))
            # Combine the strings to one string
            # Find the largest length
            max_len = np.max([len(nx_str), len(ny_str), len(nz_str)])
            # Make the strings the same length
            if len(nx_str) < max_len:
                nx_str.append('')
            if len(ny_str) < max_len:
                ny_str.append('')
            if len(nz_str) < max_len:
                nz_str.append('')
            for number in range(max_len):
                spatial_grid_possibilities.append(nx_str(number) +\
                                          ny_str(number) +\
                                          nz_str(number))

        # Set the combination of timestep and nout if set
        # Appendable lists
        temporal_grid_possibilities = []
        timestep_str = []
        nout_str     = []
        # Append the different time options to the list of strings
        if self.timestep != None:
            for timestep in self.timestep:
                timestep_str.append(' timestep=' + str(timestep))
        if self.nout != None:
            for nout in self.nout:
                nout_str.append(' nout=' + str(nout))
        # Combine the strings to one string
        # Find the largest length
        max_len = np.max([len(timestep_str), len(nout_str)])
        # Make the strings the same length
        if len(timestep_str) < max_len:
            nx_str.append('')
        if len(nout_str) < max_len:
            nout_str.append('')
        for number in range(max_len):
            temporal_grid_possibilities.append(timestep_str(number) +\
                                               nout_str(number))

        # List of the possibilities of the different variables
        list_of_possibilities = [[spatial_grid_possibilities],\
                                 [temporal_grid_possibilities]]

        # List of tuple of varibles to generate possibilities from
        variable_tuples = [\
            (self.solver,     "solver", "type"),\
            (self.grid_file,  "",       "grid"),\
            (self.ddx_first,  "ddx",    "first"),\
            (self.ddx_second, "ddx",    "second"),\
            (self.ddx_upwind, "ddx",    "upwind"),\
            (self.ddx_flux,   "ddx",    "flux"),\
            (self.ddy_first,  "ddy",    "first"),\
            (self.ddy_second, "ddy",    "second"),\
            (self.ddy_upwind, "ddy",    "upwind"),\
            (self.ddy_flux,   "ddy",    "flux"),\
            (self.ddz_first,  "ddz",    "first"),\
            (self.ddz_second, "ddz",    "second"),\
            (self.ddz_upwind, "ddz",    "upwind"),\
            (self.ddz_flux,   "ddz",    "flux"),\
            (self.MXG,        "",       "MXG"),\
            (self.MYG,        "",       "MYG"),\
            ]

        for additional in self.additional:
            variable_tuples.append(additional[0],\
                            additional[1],\
                            additional[2])


        # TODO: What is happening with additional?

        # Append the possibilities to the list of possibilities
        for var in variable_tuples:
            list_of_possibilitie.append(\
                    [self.generate_possibilities(var[0], var[1], var[2])]\
                    )

        import pdb
        pdb.set_trace()
        ##FIXME: What is happening with nproc???????????
        #             nproc      = 1,\
        #             restart    = None,\
        #             cpy_source = None,\







#        # List of all the data members
#        data_members = [self.solver, self.nproc, self.methods,\
#                        self.n_points, self.nout, self.timestep,\
#                        self.MXG, self.MYG, self.additional]
#
#        # List comprehension to get the non-none values
#        changed_members = [member for member in data_members\
#                           if member != None]
#
#
#        spatial_grid_possibilities = \
#            self.list_of_possibilities(self.n_points, changed_members, 2)
#
#
#        # Finding all combinations which can be used in the run argument
#        nproc_possibilities = \
#            self.list_of_possibilities(self.nproc, changed_members, 0,\
#            'nproc')
#        nout_possibilities = \
#            self.list_of_possibilities(self.nout, changed_members, 0,\
#            'nout')
#        MYG_possibilities = \
#            self.list_of_possibilities(self.MXG, changed_members, 0,\
#            'MXG')
#        MXG_possibilities = \
#            self.list_of_possibilities(self.MYG, changed_members, 0,\
#            'MYG')
#        timestep_possibilities = \
#            self.list_of_possibilities(self.timestep, changed_members, 1,\
#            'timestep')
#        solver_possibilities = \
#            self.list_of_possibilities(self.solver, changed_members, 1,\
#            'solver')
#        method_possibilities = \
#            self.list_of_possibilities(self.methods, changed_members, 3)
#
#        # Additional possibilities can take any form
#        if self.additional == False:
#                additional_possibilities = \
#                    self.list_of_possibilities(\
#                        self.additional, changed_members, 0)
#        else:
#            level = self.additional['level']
#            name  = self.additional['name']
#            value = self.additional['value']
#            changed_members.append(value)
#            additional_possibilities = \
#                self.list_of_possibilities(value, changed_members, level, name)
#
#        # Make the possibility list
#        possibility_list = [\
#            solver_possibilities,\
#            MYG_possibilities,\
#            MXG_possibilities,\
#            nout_possibilities,\
#            timestep_possibilities,\
#            method_possibilities,\
#            additional_possibilities,\
#            spatial_grid_possibilities,\
#            ]
#
#        # The two last return values are used in the convergence_run
#        # class
        return possibility_list, spatial_grid_possibilities, timestep_possibilities
#}}}

#{{{get_combinations
    def get_combinations(self,\
                        all_possibilities,\
                        spatial_grid_possibilities,\
                        timestep_possibilities,\
                        **kwargs):
        """ Find all combinations of the changed data members """

        # The normal way of finding all combinations
        if ('convergence_type' in list(kwargs.keys())) == False:
            all_combinations = self.list_of_combinations(all_possibilities)

        # The special way of finding all combinations
        else:
            if kwargs['convergence_type'] == 'spatial':
                # If we want to check for spatial convergence, we increase
                # the number of grid points with equal amount for all
                # directions in the grid
                # We start by removing the spatial_grid_possibilities from the
                # possibility list
                all_possibilities.remove(spatial_grid_possibilities)
            elif kwargs['convergence_type'] == 'temporal':
                # If we want to check for temporal convergence, we decrease
                # the time increment
                # Put the time_step last in the possibility list, so that we
                # are changing the timestep the fastest when making runs
                all_possibilities.remove(timestep_possibilities)
                all_possibilities.append(timestep_possibilities)

            # Find all combinations of the changed data members
            all_combinations = self.list_of_combinations( all_possibilities )


            if kwargs['convergence_type'] == 'spatial':
                # To do the convergence test, we would like all the
                # directions (nx, ny, MZ) to have the same amount of INNER
                # points  (excluding guard cells)

                # NOTE:
                # nx, ny and MZ are defined differently
                # nx = number of inner points + number of guard cells
                #      number of guard cells = 2*MXG
                # ny = number of inner points
                # MZ = number of inner points + 1 extra point
                #      (due to  historical reasons)

                # Therefore, for each combination in all_combinations, we will
                # make new combinations with the number of points given
                # in one of the keys of
                # self.n_points

                # A list to be filled with the number of grid points (the
                # range) for each direction nx, ny and MZ (if found)
                ranges = []

                # First we check if MZ is set in self.grid, as this has the
                # constraint that it needs to be on the form 2^n+1
                grid_keys = list(self.n_points.keys())
                if 'MZ' in grid_keys:
                    # If MZ is found, this is going to be the basis for the
                    # order grid numbers
                    convergence_list_z = self.n_points['MZ']
                    # The number of inner grid points
                    inner_points = [number-1 for number in\
                                    convergence_list_z]
                    # If nx is also a part of the grid list
                    if 'mesh:nx' in grid_keys:
                        # Append ranges with the nx_range
                        ranges =\
                            self.set_nx_range(grid_keys, inner_points, ranges)
                    # ny can be set with the number of inner_points
                    if 'mesh:ny' in grid_keys:
                        # Append ranges with the ny_range
                        ranges =\
                            self.set_ny_range(grid_keys, inner_points, ranges)
                    # Set the grid list in Z
                    ranges = self.set_MZ_range(grid_keys, inner_points, ranges)
                else:
                    # Check if MZ is set in BOUT.inp instead, and if MZ is over
                    # 3 (in that case inner_points must be on the form 2^n,
                    # and we need to set the MZ range)
                    MZ = find_variable_in_BOUT_inp(self.directory, 'MZ')
                    if (type(MZ) == int) and (MZ > 3):

                        # Find inner_points from either ny or nx
                        if 'ny' in grid_keys:
                            the_direction = 'mesh:ny'
                        else:
                            the_direction = 'mesh:nx'

                        min_convergence_list = min(self.n_points[the_direction])
                        max_convergence_list = max(self.n_points[the_direction])
                        # Create a range from the min and the max
                        min_power = round(math.log(min_convergence_list,2))
                        max_power = round(math.log(min_convergence_list,2))
                        inner_points =\
                            logspace(min_power, max_power,\
                                     (max_power-min_power)+1,\
                                     base=2)
                        # Convert to list
                        inner_points = list(inner_points)
                        # Convert to integers
                        inner_points = [int(point) for point in inner_points]
                        # Set the ranges
                        ranges = self.set_nx_range(grid_keys, inner_points,\
                                                   ranges)
                        ranges = self.set_ny_range(grid_keys, inner_points,\
                                                   ranges)
                        ranges = self.set_MZ_range(grid_keys, inner_points,\
                                                   ranges)
                    else:
                        # MZ is not of importance
                        # Find inner_points from either ny or nx
                        if 'mesh:ny' in grid_keys:
                            convergence_list_y = self.n_points['mesh:ny']
                            # The number of inner grid points
                            inner_points = [number for number in\
                                            convergence_list_y]
                            # If nx is also a part of the grid list
                            if 'mesh:nx' in grid_keys:
                                # Append the x range
                                ranges =\
                                    self.set_nx_range(\
                                        grid_keys, inner_points, ranges)
                            # Append the y range
                            ranges =\
                                self.set_ny_range(\
                                    grid_keys, inner_points, ranges)
                        elif 'mesh:nx' in grid_keys:
                            # Only x is of importance
                            convergence_list_x = self.n_points['mesh:nx']
                            x_range =\
                                ['mesh:nx=' + str(nr)\
                                    for nr in convergence_list_x]
                            ranges.append(x_range)

                # Make the range to a convergence string, which one can make
                # combinations from
                if len(ranges)==1:
                    convergence_zip = list(zip(ranges[0]))
                elif len(ranges)==2:
                    convergence_zip = list(zip(ranges[0], ranges[1]))
                elif len(ranges)==3:
                    convergence_zip = list(zip(ranges[0], ranges[1], ranges[2]))

                convergence_strings = [' '.join(element)\
                                       for element in convergence_zip]

                # Append the new combination to a list
                new_combinations = []
                for combination in all_combinations:
                    for grid_spacing in convergence_strings:
                        new_combinations.append(\
                            combination + ' ' + grid_spacing)
                # Make all_combinations = new_combinations
                all_combinations = new_combinations

        return all_combinations
#}}}

#{{{prepare_dmp_folder
    def prepare_dmp_folder(self, combination):
        """Get the folder to dump data in from the combination"""
        # Obtain file and folder names
        folder_name = self.get_folder_name(combination)
        # Create folder if it doesn't exists
        self.dmp_folder = self.directory + "/" + folder_name
        create_folder(self.dmp_folder)
        # Copy the input file into this folder
        command = 'cp ' + self.directory + '/BOUT.inp ' + self.dmp_folder
        shell(command)

        return
#}}}

#{{{remove_data
    def remove_data(self):
        """Removes *.nc, *.log, *.png and *.pdf files from the dump directory"""
        print("Removing old data")
        command = "rm -f ./" + self.dmp_folder +\
                  "/*.nc ./" + self.dmp_folder +\
                  "/*.log ./" + self.dmp_folder +\
                  "/*.png ./" + self.dmp_folder +\
                  "/*.pdf"
        shell(command)
#}}}

#{{{check_if_run_already_performed
    def check_if_run_already_performed(self):
        """Checks if the run has been run previously"""
        dmp_files = glob.glob(self.dmp_folder + '/BOUT.dmp.*')
        if len(dmp_files) != 0 and self.restart == False:
            print('Skipping the run as *.dmp.* files was found in '\
                  + self.dmp_folder)
            print('To overwrite old files, run with self.run(remove_old=True)\n')
            return False
        else:
            return True
#}}}

#{{{single_run
    def single_run(self, combination=''):
        """Makes a single MPIRUN of the program"""

        command = self.get_command_to_run( combination )

        tic = timeit.default_timer()
        status, out = launch(command,\
                             runcmd = self.MPIRUN,\
                             nproc = self.nproc,\
                             pipe = True,\
                             verbose = True)
        toc = timeit.default_timer()
        elapsed_time = toc - tic

        return out, elapsed_time
#}}}

#{{{append_run_log
    def append_run_log(self, start, run_no, run_time):
        """Appends the run_log"""

        # Convert seconds to H:M:S
        run_time = str(datetime.timedelta(seconds=run_time))

        start_time = (str(start.year) + '-' + str(start.month) + '-' +\
                      str(start.day) + '.' + str(start.hour) + ":" +\
                      str(start.minute) + ':' + str(start.second))

        # If the run is restarted with initial values from the last run
        if self.restart:
            dmp_line = self.dmp_folder + '-restart-'+self.restart
        else:
            dmp_line = self.dmp_folder

        # Line to write
        line = [start_time, self.run_type, run_no, dmp_line, run_time]
        # Opens for appending
        f = open(self.run_log , "a")
        f.write('    '.join(str(element) for element in line) + "\n")
        f.close()
#}}}

#{{{set_run_counter
    def set_run_counter(self, **kwargs):
        """Sets self.run_counter and self.no_runs_in_group"""

        self.run_counter = 0
        # Normally there is only one job in a group
        self.no_runs_in_group = 1

        # Due to plotting it is convenient to put runs belonging to the
        # same convergence plot into one group
        if ('convergence_type' in list(kwargs.keys())):
            if kwargs['convergence_type'] == 'spatial':
                # How many runs must we make before we can make a
                # convergence plot
                keys = list(self.n_points.keys())
                self.no_runs_in_group = len(self.n_points[keys[0]])
            elif kwargs['convergence_type'] == 'temporal':
                # How many runs must we make before we can make a
                # convergence plot
                self.no_runs_in_group = len(self.timestep)
#}}}

#{{{post_run
    def post_run(self, **kwarg):
        """In basic_runner this is a virtual function"""
        return
#}}}
#}}}

# Auxiliary functions
# FIXME: Mention that the data can be set to either string or iterable
# FIXME: Mention that nx, ny and nz need to be of the same length
# FIXME: Mention that timestep and nout need to be of the same length
# FIXME: Mention that MXG, MYG need to be of the same length
#{{{
#{{{set_member_data
    def set_member_data(self, input_parameter):
        """Returns the input_parameter as a list if it is different than None,
        and if it is not iterable"""

       # If the input_data is not set, the value in BOUT.inp will
       # be used
        if input_parameter != None:
            # If the input_data is not an iterable, or if it is a
            # string: Put it to a list
            if not(hasattr(input_parameter, "__iter__")) or\
               (type(input_parameter)) == str:
                input_parameter = [input_parameter]

        return input_parameter
#}}}

#{{{basic_error_check
    def basic_error_check(self, remove_old):
        """Check if there are any type errors in the data members"""

        # nproc and directory is set by default, however, we must check that
        # the user has not given them as wrong input
        if type(self.nproc) != int:
            message  = "nproc is of wrong type\n"+\
                       "nproc must be given as an int"
            self.errors.append("TypeError")
            raise TypeError(message)
        if type(self.directory) != str:
            message  = "directory is of wrong type\n"+\
                       "directory must be given as a str"
            self.errors.append("TypeError")
            raise TypeError(message)

        # Check if there are any BOUT.inp files in the self.directory
        inp_file = glob.glob(self.directory + "/BOUT.inp")
        if len(inp_file) == 0:
            self.errors.append("RuntimeError")
            raise RuntimeError("No BOUT.inp files found in '" +\
                                self.directory + "'")

        # Check if the following is an integer, or an iterable
        # containing only integers
        check_if_int = [\
            (self.nx        , 'nx')        ,\
            (self.ny        , 'ny')        ,\
            (self.nz        , 'nz')        ,\
            (self.nout      , 'nout')      ,\
            (self.MXG       , 'MXG')       ,\
            (self.MYG       , 'MYG')        \
            ]

        self.check_for_correct_type(var = check_if_int,\
                                    the_type = int)

        # Check if the following is a number
        check_if_number = [\
            (self.timestep  , 'timestep')\
            ]

        self.check_for_correct_type(var = check_if_number,\
                                    the_type = Number)

        # Check if instance is string, or an iterable containing strings
        check_if_string = [\
            (self.solver    , 'solver')    ,\
            (self.grid_file , 'grid_file') ,\
            (self.ddx_first , 'ddx_first') ,\
            (self.ddx_second, 'ddx_second'),\
            (self.ddx_upwind, 'ddx_upwind'),\
            (self.ddx_flux  , 'ddx_flux')  ,\
            (self.ddy_first , 'ddy_first') ,\
            (self.ddy_second, 'ddy_second'),\
            (self.ddy_upwind, 'ddy_upwind'),\
            (self.ddy_flux  , 'ddy_flux')  ,\
            (self.ddz_first , 'ddz_first') ,\
            (self.ddz_second, 'ddz_second'),\
            (self.ddz_upwind, 'ddz_upwind'),\
            (self.ddz_flux  , 'ddz_flux')  ,\
            ]

        self.check_for_correct_type(var = check_if_string,\
                                    the_type = str)

        # Check if the solver is possible
        # From /include/bout/solver.hxx
        possible_solvers = [\
            'cvode',\
            'pvode',\
            'ida',\
            'petsc',\
            'karniadakis',\
            'rk4',\
            'euler',\
            'rk3ssp',\
            'power',\
            'arkode'\
            ]

        # Do the check if the solver is set
        if self.solver != None:
            self.check_if_possible(var = (self.solver, 'solver'),\
                                  possibilities = possible_solvers)

        # Check if ddx or ddy is possible
        possible_method = [\
            'C2',\
            'C4',\
            'W2',\
            'W3'\
            ]

        # Make a list of the variables
        the_vars = [\
            (self.ddx_first , 'ddx_first') ,\
            (self.ddx_second, 'ddx_second'),\
            (self.ddy_first , 'ddy_first') ,\
            (self.ddy_second, 'ddy_second')\
            ]

        for var in the_vars:
            # Do the check if the method is set
            if var[0] != None:
                self.check_if_possible(var           = var,\
                                       possibilities = possible_method)

        # Check if ddz is possible
        possible_method.append('FFT')

        # Make a list of the variables
        the_vars = [\
            (self.ddz_first , 'ddz_first') ,\
            (self.ddz_second, 'ddz_second') \
            ]

        for var in the_vars:
            # Do the check if the method is set
            if var[0] != None:
                self.check_if_possible(var           = var,\
                                       possibilities = possible_method)

        # Check for upwind terms
        possible_method = [\
            'U1',\
            'U4',\
            'W3'\
            ]

        # Make a list of the variables
        the_vars = [\
            (self.ddx_upwind, 'ddx_upwind'),\
            (self.ddy_upwind, 'ddy_upwind'),\
            (self.ddz_upwind, 'ddz_upwind')\
            ]

        for var in the_vars:
            # Do the check if the method is set
            if var[0] != None:
                self.check_if_possible(var          = var,\
                                       possibilities = possible_method)

        # Check for flux terms
        possible_method = [\
            'SPLIT',\
            'NND'\
            ]

        # Make a list of the variables
        the_vars = [\
            (self.ddx_flux  , 'ddx_flux'),\
            (self.ddy_flux  , 'ddy_flux'),\
            (self.ddz_flux  , 'ddz_flux')\
            ]

        for var in the_vars:
            # Do the check if the method is set
            if var[0] != None:
                self.check_if_possible(var           = var,\
                                       possibilities = possible_method)

        # Check if restart is set correctly
        if self.restart != None:
            if type(self.restart) != str:
                self.errors.append("TypeError")
                raise TypeError ("restart must be set as a string when set")

        possible_method = [\
            'overwrite',\
            'append'\
            ]

        # Make a list of the variables
        the_vars = [\
            (self.restart, 'restart')\
            ]

        for var in the_vars:
            # Do the check if the method is set
            if var[0] != None:
                self.check_if_possible(var           = var,\
                                       possibilities = possible_method)

        # Check if nx, ny, nz and gridfile is set at the same time
        if (self.nx != None and self.grid_file != None) or\
           (self.ny != None and self.grid_file != None) or\
           (self.nz != None and self.grid_file != None):
            # Read the variable from the file
            for grid_file in self.grid_file:
                # Open (and automatically close) the grid files
                f = DataFile(grid_file)
                # Search for nx, ny and nz in the grid file
                domain_types = ["nx", "ny", "nz"]
                for domain_type in domain_types:
                    grid_variable = f.read(domain_type)
                    # If the variable is found
                    if grid_variable != None:
                        self.errors.append("TypeError")
                        message  = domain_type + " was specified both in the "
                        message += "driver and in the grid file.\n"
                        message += "Please remove " + domain_type
                        message += " from the driver if you would "
                        message += "like to run with a grid file."
                        raise TypeError(message)

        # If grid files are set, use the nx, ny and nz values in the
        # member data if applicable
        if self.grid_file != None:
            # Make a dict of appendable lists
            spatial_domain = {'nx':[], 'ny':[], 'nz':[]}
            for grid_file in self.grid_file:
                # Open (and automatically close) the grid files
                f = DataFile(grid_file)
                # Search for nx, ny and nz in the grid file
                domain_types = ["nx", "ny", "nz"]
                for domain_type in domain_types:
                    grid_variable = f.read(domain_type)
                    # If the variable is found
                    if grid_variable != None:
                        spatial_domain[domain_type].append(grid_variable)
            # Check that the lengths of nx, ny and nz are the same
            # unless they are not found
            len_nx = len(spatial_domain['nx'])
            len_ny = len(spatial_domain['ny'])
            len_nz = len(spatial_domain['nz'])
            if len_nx != 0:
                self.nx = spatial_domain['nx']
            if len_ny != 0:
                self.ny = spatial_domain['ny']
            if len_nz != 0:
                self.nz = spatial_domain['nz']

        # Check that nx, ny and nz are set correctly
        if self.nx != None and self.ny != None:
            self.check_same_length((self.nx, 'nx'), (self.ny, 'ny'))
        if self.nx != None and self.nz != None:
            self.check_same_length((self.nx, 'nx'), (self.nz, 'nz'))
        if self.ny != None and self.nz != None:
            self.check_same_length((self.ny, 'ny'), (self.nz, 'nz'))

        # Check that timestep and nout are set correctly
        if self.timestep != None and self.nout != None:
            self.check_same_length((self.timestep, 'timestep'),\
                                   (self.nout, 'nout'))

        # Check that MXG and MYG are set correctly
        if self.MXG != None and self.MYG != None:
            self.check_same_length((self.MXG, 'MXG'), (self.MYG, 'MYG'))

        # additional should be on the form
        # additional = [(section1, name1, [value1-1, value1-2, ...]),\
        #               (section2, name2, [value2-1, value2-2, ...]),\
        #               ...]
        # We will now check that
        if self.additional != None:
            # Set a success variable that will fail if anything goes
            # wrong
            success = True
            # Check if self.addition is iterable
            if hasattr(self.additional, "__iter__"):
                # Check if self.additional is a string
                if type(self.additional) != str and\
                   type(self.additional) != dict:
                    # If additional is given as an iterable
                    if hasattr(self.additional[0], "__iter__" ):
                        # Do the same check as above for all the
                        # elements
                        for elem in self.additional:
                            # Check if self.addition is iterable
                            if hasattr(elem, "__iter__"):
                                # Check if elem is a string
                                if type(elem) != str:
                                    if type(elem[0]) == str:
                                        # Check that the second element
                                        # (the name) is a string
                                        if type(elem[1]) != str:
                                            success = False
                                        # If more than three elements
                                        # are given
                                        if len(elem) != 3:
                                            success = False
                                    # elem[0] is not a string
                                    else:
                                        success = False
                                # elem is a string
                                else:
                                    success = False
                            # elem is not iterable
                            else:
                                success = False
                    # self.additional[0] is not a string, and not iterable
                    else:
                        success = False
                # self.additional is a string or a dict
                else:
                    success = False
            # self.additional is not iterable
            else:
                success = False
            if not(success):
                message  = "self.additional is on the wrong form.\n"
                message += "self.additional should be on the form\n"
                message += "self.additional=\ \n"
                message +=\
                        "     [(section1, name1, [value1-1, value1-2,...]),\ \n"
                message +=\
                        "      (section2, name2, [value2-1, value2-2,...]),\ \n"
                message +=\
                        "       ...])\n"
                self.errors.append("TypeError")
                raise TypeError(message)

        # Check if grid_file is a string
        if self.grid_file != None:
            # Set a variable which is has length over one if the test fails
            not_found = []
            if type(self.grid_file) == str:
                # See if the grid_file can be found
                grid_file = glob.glob(self.grid_file)
                # The grid_file cannot be found
                if len(grid_file) == 0:
                    not_found.append(self.grid_file)
            # If several grid files are given
            elif hasattr(self.grid_file, "__iter__"):
                for elem in self.grid_file:
                    # See if the grid_file can be found
                    grid_file = glob.glob(elem)
                    # The grid_file cannot be found
                    if len(grid_file) == 0:
                        not_found.append(elem)
            if len(not_found) > 0:
                message =  "The following grid files were not found\n"
                message += "\n".join(not_found)
                self.errors.append("RuntimeError")
                raise RuntimeError(message)

        # Check if boolean
        check_if_bool = [\
            (self.cpy_source, 'cpy_source'),\
            (self.allow_size_modification, 'allow_size_modification')\
            ]

        self.check_for_correct_type(var = check_if_bool,\
                                    the_type = bool)

        # Check if remove_old and restart is set on the same time
        if remove_old == True and self.restart != None:
            self.errors.append("RuntimeError")
            raise RuntimeError("You should not remove old data if you"\
                               " want a restart run")
#}}}

#{{{check_for_correct_type
    def check_for_correct_type(self,\
                               var      = None,\
                               the_type = None):
        """Checks if a varible has the correct type

        Input:
        var      - a tuple consisting of
                   var[0] - the variable (a data member)
                   var[1] - the name of the varible given as a string
        the_type - the data type"""

        # Set a variable which is False if the test fails
        success = True
        for cur_var in var:
            # There is an option that the variable could be set to None,
            # and that the default value from BOUT.inp will be used
            if cur_var[0] != None:
                # Check for the correct type
                if isinstance(cur_var[0], the_type) == False:
                    # Check if it is an iterable
                    if hasattr(cur_var[0], "__iter__") and\
                       type(cur_var[0]) != dict:
                        for elem in cur_var[0]:
                            # Check for the correct type
                            if isinstance(elem, the_type) == False:
                                success = False
                    else:
                        # Neither correct type, nor iterable
                        success = False
                if not(success):
                    message  = cur_var[1] + " is of wrong type\n"+\
                               cur_var[1] + " must be " + the_type.__name__  +\
                               " or an iterable with " + the_type.__name__ +\
                               " as elements."
                    self.errors.append("TypeError")
                    raise TypeError(message)
#}}}

#{{{check_if_possible
    def check_if_possible(self,\
                          var           = None,\
                          possibilities = None):
        """Check if a variable is set to a possible variable"""

        # Set a variable which is False if the test fails
        success = True

        # Due to the check done in check_for_correct_type: If the
        # variable is not a string it will be an iterable
        if type(var[0]) != str:
            for elem in var[0]:
                # Check if the element is contained in the possibilities
                if not(elem in possibilities):
                    success = False
        else:
            # The variable was a string
            if not(var[0] in possibilities):
                success = False

        if not(success):
            message = var[1] + " was not set to a possible option.\n"+\
                      "The possibilities are \n" + "\n".join(possibilities)
            self.errors.append("TypeError")
            raise TypeError(message)
#}}}

#{{{check_same_length
    def check_same_length(self, object1 = None, object2 = None):
        """Checks if object1 and object2 has the same length

        Input:
        object1 - a tuple of the object and its name
        object2 - a tuple an object different than object1 together with
                  its name
        """

        try:
            len_dim1 = len(object1[0])
        # If nx does not have length
        except TypeError:
            len_dim1 = 1
        try:
            len_dim2 = len(object2[0])
        # If nx does not have length
        except TypeError:
            len_dim2 = 1

        if len_dim1 != len_dim2:
            message = object1[1] + " and " + object2[1] + " must have the same"
            message += " length when specified"
            self.errors.append("RuntimeError")
            raise RuntimeError (message)
#}}}

#{{{get_folder_name
    def get_folder_name(self, combination):
        """Returning a file name and a folder name.
         The folder name will be on the form solver/methods_used.
         The file name will be the rest of the combination string."""

        # Combination is one of the combination of the data members
        # which is used as the command line arguments in the run
        combination = combination.split()

        # Appendable data types
        solver = ''
        methods=[]
        guard_nout_timestep = []
        grid_folder = []
        rm=[]
        directions = ['ddx', 'ddy', 'ddz']
        n_points = ['nx', 'ny', 'MZ']

        for expression in combination:
            # Set solver, MYG, MXG, nout and timestep to be removed from
            # the combination  string
            if 'solver' in expression:
                # See http://www.tutorialspoint.com/python/python_reg_expressions.htm
                # for regex explanation
                # Extract the solver type
                solver = re.sub(r"^.*=", "", expression)
                rm.append(expression)
            elif ('MXG' in expression) or ('MYG' in expression)\
                 or ('nout' in expression) or ('timestep' in expression):
                # Remove these from the name as they do not vary
                rm.append(expression)
                guard_nout_timestep.append(expression)
            elif 'timestep' in expression and len(self.timestep) == 1:
                # Remove this from the name if it doesn't change
                rm. append(expression)
            # The following could be nicely done with
            # elif any(direction in expression for direction in directions):
            # however, any(iterable) has a strange behavior in ipython,
            # therefore a more brute force method is used
            else:
                # Finding the method folder
                for direction in directions:
                    if direction in expression:
                        # We append methods as a part of the folder name
                        methods.append(expression.replace(':','-'))
                        rm.append(expression)
                # Finding the grid folder
                for grid in n_points:
                    if grid in expression:
                        # Append the grid as a part of the folder name
                        grid_folder.append(expression.replace(':','-'))
                        rm.append(expression)

        # Remove the solver and method elements in combinations
        for element in rm:
            combination.remove(element)

        # Convert the list to strings
        methods = '_'.join(methods)
        guard_nout_timestep = '_'.join(guard_nout_timestep)
        grid_folder = '_'.join(grid_folder)
        # The rest in the combination is whatever is in self.additional
        additional_folder ='_'.join(combination)

        # Write the folder path
        if solver == '' and methods == '':
            combination_folder = 'solver_and_methods_unchanged'
        elif solver == '':
            combination_folder = 'solver_unchanged/' + methods
        elif methods == '':
            combination_folder = solver + '/methods_unchanged'
        else:
            combination_folder = solver + '/' + methods

        # Append the folder path if not empty
        if additional_folder != '':
            combination_folder += '/' + additional_folder
        if guard_nout_timestep != '':
            combination_folder += '/' + guard_nout_timestep
        if grid_folder != '':
            combination_folder += '/' + grid_folder

        # Replace unwanted characters
        combination_folder = combination_folder.replace('=','-')
        combination_folder = combination_folder.replace(':','-')

        return combination_folder
#}}}

#{{{get_correct_domain_split
    def get_correct_domain_split(self):
        """Checks that the grid can be split in the correct number of
        processors. If not, vary the number of points until value is found."""

        # Flag which is True when a warning should be produce
        produce_warning = False

        for size_nr in range(len(self.nx)):
            split_found = False
            add_number = 1
            print("Check grid split for mesh")
            while split_found == False:
                # The same check as below is performed internally in
                # BOUT++ (see boutmesh.cxx)
                # FIXME: YOU MAY HAVE DIFFERENT MXG
                for i in range(1, self.nproc+1, 1):
                    MX = self.nx[size_nr] - 2*self.MXG
                    if (self.nprocs % i == 0) and \
                       (MX % i == 0) and \
                       (self.ny[size_nr] % (self.nprocs/i) == 0):
                        # If the test passes
                        split_found = True

                # If the value tried is not a good value
                if split_found == False:
                    # If modification is allowd
                    if self.allow_size_modification and self.grid_file == None:
                        # Produce a warning
                        produce_warning = True
                        self.nx[size_nr] += add_number
                        self.ny[size_nr] += add_number
                        print("Mismatch, trying "+ str(self.nx[size_nr]) +\
                              "*" + str(self.ny[size_nr]))
                        add_number = (-1)**(abs(add_number))\
                                     *(abs(add_number) + 1)
                    else:
                        # If the split fails and the a grid file is given
                        if self.grid_file != None:
                            self.errors.append("RuntimeError")
                            message = "The grid can not be split using the"+\
                                      " current number of nproc"
                            raise RuntimeError(message)
                        # If the split fails and no grid file is given
                        else:
                            self.errors.append("RuntimeError")
                            message  = "The grid can not be split using the"+\
                                       " current number of nprocs.\n"
                            message += "Setting allow_size_modification=True"+\
                                       " will allow modification of the grid"+\
                                       " so that it can be split with the"+\
                                       " current number of nprocs"
                            raise RuntimeError(message)
            # When the good value is found
            print("Sucessfully found good values for the mesh.")
            print("New mesh x=" + str(self.nx[size_nr]) + " y=" + str(self.ny[size_nr]))

            # Make the warning
            if produce_warning:
                message = "The mesh was changed to allow the split given by nproc"
                self.warnings.append(message)
#}}}

# TODO: Delete this function
#{{{list_of_possibilities
    def list_of_possibilities(\
        self, data_member, changed_member, level, data_member_name = None):
        """Returns the different possibilities as a list of strings.
        level=0 denotes a data_member given as a number.
        level=1 denotes a data_member given as a list.
        level=2 denotes a data_member given as a dictionary of lists..
        level=3 denotes a data_member given as a dictionary of dictionary of lists."""

        if data_member in changed_member:
            if level == 0:
                return [data_member_name + "=" + str(data_member)]
            elif level == 1:
                if data_member_name == 'solver':
                    possibilities = ["solver:type=" + possibility \
                                     for possibility in data_member]
                    return possibilities
                elif data_member_name == 'timestep':
                    possibilities = ["timestep=" + str(possibility) \
                                     for possibility in data_member]
                    return possibilities
                else:
                    # The data_member_name comes from self.additional
                    possibilities = [data_member_name + "=" + str(possibility) \
                                     for possibility in data_member]
                    return possibilities
            elif level == 2:
                data_member_as_list = \
                    self.level_1_dictionary_to_level_2_list( data_member )
                return self.list_of_combinations( data_member_as_list )
            elif level == 3:
                data_member_as_list = \
                    self.level_2_dictionary_to_level_2_list( data_member )
                return self.list_of_combinations( data_member_as_list )
        else:
            return ['']
#}}}

#{{{generate_posssibilities
    def generate_possibilities(self, variables=None, section=None, name=None):
        """Generate the list of strings of possibilities"""

        if variables != None:
            # Set the section name correctly
            if section != None:
                section = section + ":"
            else:
                section = ""
            # Set the combination of the varibale
            var_possibilities = []
            # Find the number of different dimensions
            for var in variables:
                var_possibilities.append(' ' + section + name + '=' + str(var))
#}}}

# TODO: Delete this function
#{{{level_1_dictionary_to_level_2_list
    def level_1_dictionary_to_level_2_list(self, level_1_dictionary):
        """Takes a dictionary with an iterable as values.
        Returns a list of a list. The elements of each innermost
        list are strings containing all possible choices of key=val,
        where key is the key of the level 1 dictionary, and val is a element
        of the iterable in the innermost dictionary"""

        list_of_lists=[]
        # Iterate over a dictionary, (the for-loop returns both key and value)
        for key, val in list(level_1_dictionary.items()):
            list_of_possibilities = []
            # Iterates over the iterable (for example list) in the value of
            # the innermost dictionary
            for the_iterated in val:
                list_of_possibilities.append(key+"="+str(the_iterated))
            list_of_lists.append(list_of_possibilities)

        return list_of_lists
#}}}

# TODO: Delete this function
#{{{level_2_dictionary_to_level_2_list
    def level_2_dictionary_to_level_2_list(self, level_2_dictionary):
        """Takes a dictionary with dictionaries as values, where the values of
        the subdictionaries are iterables.
        For each subdictionaries in the dictionary, the function will
        find what will be referred to as a subcombination. The function
        will in the end return a list where the elements are lists of
        the subcombinations.
        A subcombination is a combination which contains one element
        from each of the values of the keys in the subdictionary. The
        subcombinations will the form
        'key11:key21=val_of_21 key11:key22=val_of_22 ...
         key1n:key2m=val_of_2m',
        where in keyij, i refers to the level of the dictionary (2 being
        the subdictionary) an j refers to the number of key"""

        # Appendable list_of_lists which in the end will be returned
        list_of_lists = []
        # Find the uppermost (first level) keys in the dictionary
        uppermost_keys = list(level_2_dictionary.keys())

        for upper_key in uppermost_keys:
            # Appendable list which we will find a subcombo from
            find_subcombo_from = []
            # Find the lowermost (second level) keys in the dictionary
            lowermost_keys = list(level_2_dictionary[upper_key].keys())
            for lower_key in lowermost_keys:
                # List to collect string with the same second level key
                list_with_same_lower_key = []
                for element in level_2_dictionary[upper_key][lower_key]:
                    # Append the string
                    list_with_same_lower_key.append(\
                        upper_key + ':' + lower_key + '=' + element)
                find_subcombo_from.append(list_with_same_lower_key)
            # Find the subcombo
            subcombo = self.list_of_combinations(find_subcombo_from)
            # Append the subcombo
            list_of_lists.append(subcombo)

        return list_of_lists
#}}}

#{{{list_of_combinations
    def list_of_combinations(self, input_list):
        """ Takes a list with lists as element as an input.
        Returns a list of all combinations between the elements of the
        lists of the input list """

        all_combinations_as_tuple = list(itertools.product(*input_list))
        all_combinations_as_strings = []

        # If the input_list only contains one list (corresponds to a
        # level below 2 in list_of_possibilities)
        if len(all_combinations_as_tuple[0]) == 1:
            # Loop over all the tuples in the innermost list
            for combination in all_combinations_as_tuple:
                # Store the elements of the innermost list as strings in a
                # list
                # (The zeroth element unwraps the list)
                all_combinations_as_strings.append(' ' + combination[0])
        # If the input_list contains more than one list (corresponds to
        # a level above 2 in list_of_possibilities)
        else:
            # Loop over the elements in the list containing tuples
            for a_tuple in all_combinations_as_tuple:
                string = ''
                # Loop over all the elements of the tuple
                for element in a_tuple:
                    # Make the elements of the tuple into one string
                    string += ' ' + element
                # Store the string in a list
                all_combinations_as_strings.append(string)

        return all_combinations_as_strings
#}}}

#{{{get_command_to_run
    def get_command_to_run(self, combination):
        """ Returns a string of the command which will run the BOUT++
        program"""
        # Creating the arguments
        arg = " -d " + self.dmp_folder + combination

        # If the run is restarted with initial values from the last run
        if self.restart != False:
            if self.restart == 'overwrite':
                arg += ' restart'
            elif self.restart == 'append':
                arg += ' restart append'
            else:
                self.errors.append("TypeError")
                raise TypeError ("self.restart must be set to either"+\
                                 " 'overwrite' or 'append'")

        # Replace excessive spaces with a single space
        arg = ' '.join(arg.split())
        command = "./" + self.program_name + " " + arg

        return command
#}}}

#{{{make
    def make(self):
        """Makes the .cxx program, saves the make.log and make.err"""
        print("Making the .cxx program")
        command = "make > make.log 2> make.err"
        shell(command)
        # Check if any errors occured
        if os.stat("make.err").st_size != 0:
            self.errors.append("RuntimeError")
            raise RuntimeError("Error encountered during make, see 'make.err'.")
#}}}
#}}}
#}}}



#{{{class run_with_plots
class run_with_plots(basic_runner):
#{{{docstring
    """Class running BOUT++ in the same way as the basic_runner, with
    the additional feature that it calls one of the plotters in
    'bout_plotters'.

    For further details, see the documentation of basic_runner.
    """
#}}}

# The constructor
#{{{__init__
    def __init__(self,\
                 plot_type  = False,\
                 extension  = 'png',\
                 solver     = False,\
                 nproc      = 1,\
                 methods    = False,\
                 n_points   = False,\
                 directory  = 'data',\
                 nout       = False,\
                 timestep   = False,\
                 MXG        = False,\
                 MYG        = False,\
                 additional = False,\
                 restart    = False,\
                 **kwargs):
        """Specify either how many time indices you want to plot in one
        plot, or give a list of time indices. If both are given, then the
        list of plot_times has higher precedence."""

        # Note that the constructor accepts additional keyword
        # arguments. This is because the constructor can be called with
        # 'super' from qsub_run_with_plots, which inherits from both
        # basic_qsub_runner and run_with_plots (which takes different
        # arguments as input)

        # Call the constructor of the superclass
        super(run_with_plots, self).__init__(solver     = solver,\
                                             nproc      = nproc,\
                                             methods    = methods,\
                                             n_points   = n_points,\
                                             directory  = directory,\
                                             nout       = nout,\
                                             timestep   = timestep,\
                                             MXG        = MXG,\
                                             MYG        = MYG,\
                                             additional = additional,\
                                             restart    = restart,\
                                             **kwargs)

        if plot_type == False:
            self.errors.append("TypeError")
            raise TypeError ("Keyword argument 'plot_type' must be given"+\
                             " when running run_with_plots")

        self.plot_type           = plot_type
        self.file_extension      = extension
        self.run_type            = 'plot_' + self.plot_type

        # Check if a DISPLAY is set
        try:
            os.environ['DISPLAY']
        except KeyError:
            message =  "No display is set! Changing the backend to 'Agg' in"+\
                       " order to plot."
            self.warnings.append(message)
            warning_printer(message)
            import matplotlib.pyplot as plt
            plt.switch_backend('Agg')
#}}}

# Functions called directly by the main function
#{{{
#{{{error_checker
    def error_checker(self, **kwargs):
        """Checks for errors related to the relevant plotter to the current
        class"""

        # Since the error checkers should be called from both
        # bout_runners and bout_plotters, the error_checkers have been
        # put in the class check_for_plotters_errors defined in
        # common_bout_functions
        # The error checker is called by the constructor, so all we have
        # to do is to create an instance of the class
        plotter_error_checker =\
           check_for_plotters_errors(self.plot_type, n_points=self.n_points,
                                     timestep=self.timestep, **kwargs)
#}}}

#{{{post_run
    def post_run(self, **kwargs):
        """Calls self.plotter_chooser"""
        self.plotter_chooser(**kwargs)
#}}}
#}}}

# Plotter specific
#{{{
#solution_plot specific
#{{{
#{{{solution_plotter
    def solution_plotter(self,\
            show_plots = False,\
            collect_x_ghost_points = False, collect_y_ghost_points = False,\
            **kwargs):
        """Calls the correct plotter from bout_plotters"""

        # Creates an instance of solution_plotter
        make_my_sol_plot = solution_plotter(\
            run_groups             = self.run_groups,\
            directory              = self.directory,\
            file_extension         = self.file_extension,\
            show_plots             = show_plots,\
            collect_x_ghost_points = collect_x_ghost_points,\
            collect_y_ghost_points = collect_y_ghost_points,\
            variables              = kwargs['variables'],\
            plot_direction         = kwargs['plot_direction'],\
            plot_times             = kwargs['plot_times'],\
            number_of_overplots    = kwargs['number_of_overplots'])

        # Run the plotter
        make_my_sol_plot.collect_and_plot()
#}}}
#}}}

#solution_and_error_plotter specific
#{{{
#{{{solution_and_error_plotter
    def solution_and_error_plotter(self,\
            show_plots = False,\
            collect_x_ghost_points = False, collect_y_ghost_points = False,\
            **kwargs):
        """Calls the correct plotter from bout_plotters"""

        # Creates an instance of solution_and_error_plotter
        make_my_sol_err_plot = solution_and_error_plotter(\
            run_groups             = self.run_groups,\
            directory              = self.directory,\
            file_extension         = self.file_extension,\
            show_plots             = show_plots,\
            collect_x_ghost_points = collect_x_ghost_points,\
            collect_y_ghost_points = collect_y_ghost_points,\
            variables              = kwargs['variables'],\
            plot_direction         = kwargs['plot_direction'],\
            plot_times             = kwargs['plot_times'],\
            number_of_overplots    = kwargs['number_of_overplots'])

        # Run the plotter
        make_my_sol_err_plot.collect_and_plot()
#}}}

#{{{get_plot_times_and_number_of_overplots
    def get_plot_times_and_number_of_overplots(self, **kwargs):
        """Returns plot_times and number_of_overplots"""

        if self.plot_type == 'solution_and_error_plot' or\
           self.plot_type == 'solution_plot':
            kwarg_keys = list(kwargs.keys())

            if ('plot_times' in kwarg_keys) == False:
                plot_times = False
            else:
                plot_times = kwargs['plot_times']
            if ('number_of_overplots' in kwarg_keys) == False:
                number_of_overplots = False
            else:
                number_of_overplots = kwargs['number_of_overplots']

        return plot_times, number_of_overplots
#}}}
#}}}

#convergence_plot specific
#{{{
#{{{convergence_plotter
    def convergence_plotter(self,\
            show_plots = False,\
            collect_x_ghost_points = False, collect_y_ghost_points = False,\
            **kwargs):
        """Calls the convergence plotter from bout_plotters"""
        # Creates an instance of convergence_plotter
        make_my_convergence_plots = convergence_plotter(\
           run_groups             =  self.run_groups,\
           directory              =  self.directory,\
           file_extension         =  self.file_extension,\
           show_plots             =  show_plots,\
           collect_x_ghost_points =  collect_x_ghost_points,\
           collect_y_ghost_points =  collect_y_ghost_points,\
           variables              =  kwargs['variables'],\
           convergence_type       =  kwargs['convergence_type'])

        # Run the plotter
        make_my_convergence_plots.collect_and_plot()
#}}}

#{{{set_nx_range
    def set_nx_range(self, grid_keys, inner_points, ranges):
        """Append ranges (a list filled with the number of grid points) with
        the grid points in nx (given from the list 'inner ranges')"""
        # We must find the guard cells in x to find the
        # correct nx
        # We search first if MXG is set
        if self.MXG:
            MXG = self.MXG
        else:
            # We must find it in the input file
            MXG = find_variable_in_BOUT_inp(self.directory,\
                                            'MXG')
            # If MXG was not found
            if type(MXG) == str:
                # MXG is set to the default value
                MXG = 2
        # Write the range to a list of strings
        # Set the x_range
        x_range = ['mesh:nx=' + str(nr+2*MXG) for nr in \
                   inner_points]
        ranges.append(x_range)
        return ranges
#}}}

#{{{set_ny_range
    def set_ny_range(self, grid_keys, inner_points, ranges):
        """Append ranges (a list filled with the number of grid points) with
        the grid points in ny (given from the list 'inner_points')"""
        # ny is the number of inner_points
        # Write the range to a list of strings
        # Set the y_range
        y_range = ['mesh:ny=' + str(nr) for nr in inner_points]
        ranges.append(y_range)
        return ranges
#}}}

#{{{set_nz_range
    def set_MZ_range(self, grid_keys, inner_points, ranges):
        """Append ranges (a list filled with the number of grid points) with
        the grid points in MZ (given from the list 'inner_points')"""
        # MZ is the number of inner_points + 1
        # Write the range to a list of strings
        # Set the z_range
        z_range = ['MZ=' + str(nr+1) for nr in inner_points]
        ranges.append(z_range)
        return ranges
#}}}
#}}}
#}}}

# Auxiliary functions
#{{{
#{{{plotter_chooser
    def plotter_chooser(self, **kwargs):
        """Calls the correct plotter from bout_plotters"""

        # Set option
        kwarg_keys = list(kwargs.keys())
        if 'show_plots' in kwarg_keys:
            show_plots = kwargs['show_plots']
        else:
            show_plots = False
        if 'collect_x_ghost_points' in kwarg_keys:
            collect_x_ghost_points = kwargs['collect_x_ghost_points']
        else:
            collect_x_ghost_points = False
        if 'collect_y_ghost_points' in kwarg_keys:
            collect_y_ghost_points = kwargs['collect_y_ghost_points']
        else:
            collect_y_ghost_points = False

        if self.plot_type == 'solution_and_error_plot' or\
           self.plot_type == 'solution_plot':
            # Get the plot_times or the number_of_overplots (one may
            # have to be set to False if not given by the user input)
            plot_times, number_of_overplots =\
                self.get_plot_times_and_number_of_overplots(**kwargs)

            if self.plot_type == 'solution_plot':
                # Call the solution plotter
                self.solution_plotter(\
                    plot_times = plot_times,\
                    number_of_overplots = number_of_overplots,\
                    show_plots = show_plots,\
                    collect_x_ghost_points = collect_x_ghost_points,\
                    collect_y_ghost_points = collect_y_ghost_points,\
                    variables = kwargs['variables'],\
                    plot_direction = kwargs['plot_direction'])
            elif self.plot_type == 'solution_and_error_plot':
                # Call the solution and error plotter
                self.solution_and_error_plotter(\
                    plot_times = plot_times,\
                    number_of_overplots = number_of_overplots,\
                    show_plots = show_plots,\
                    collect_x_ghost_points = collect_x_ghost_points,\
                    collect_y_ghost_points = collect_y_ghost_points,\
                    variables = kwargs['variables'],\
                    plot_direction = kwargs['plot_direction'])
        elif self.plot_type == 'convergence_plot':
            # Call the convergence_plotter
            self.convergence_plotter(\
                show_plots = show_plots,\
                collect_x_ghost_points = collect_x_ghost_points,\
                collect_y_ghost_points = collect_y_ghost_points,\
                variables = kwargs['variables'],\
                convergence_type = kwargs['convergence_type'])
        else:
            self.errors.append("TypeError")
            raise TypeError ("The given 'plot_type' '" + str(self.plot_type) +\
                             "' is invalid. See run_with_plots"+\
                             " documentation for valid possibilities.")
#}}}
#}}}
#}}}



#{{{basic_qsub_runner
class basic_qsub_runner(basic_runner):
#{{{docstring
    """Class for running BOUT++.
    Works like the basic_runner, but submits the jobs to a torque queue
    with qsub.

    The link below gives a nice introduction to the qsub system
    http://wiki.ibest.uidaho.edu/index.php/Tutorial:_Submitting_a_job_using_qsub"""
#}}}

# The constructor
#{{{__init__
    def __init__(self,\
                 nodes      = '1',\
                 ppn        = '4',\
                 walltime   = '50:00:00',\
                 mail       = False,\
                 queue      = False,\
                 solver     = False,\
                 nproc      = 1,\
                 methods    = False,\
                 n_points   = False,\
                 directory  = 'data',\
                 nout       = False,\
                 timestep   = False,\
                 MYG        = False,\
                 MXG        = False,\
                 additional = False,\
                 restart    = False,\
                 **kwargs):
        """The values in the constructor determines the torque job
        is submitted."""

        # Note that the constructor accepts additional keyword
        # arguments. This is because the constructor can be called with
        # 'super' from qsub_run_with_plots, which inherits from both
        # basic_qsub_runner and run_with_plots (which takes different
        # arguments as input)

        # Call the constructor of the superclass
        super(basic_qsub_runner, self).__init__(solver     = solver,\
                                                nproc      = nproc,\
                                                methods    = methods,\
                                                n_points   = n_points,\
                                                directory  = directory,\
                                                nout       = nout,\
                                                timestep   = timestep,\
                                                MYG        = MYG,\
                                                MXG        = MXG,\
                                                additional = additional,\
                                                restart    = restart,\
                                                **kwargs)

        self.nodes      = nodes
        # Processors per node
        self.ppn        = ppn
        self.walltime   = walltime
        self.mail       = mail
        self.queue      = queue
        self.run_type   = 'basic_qsub'
        # A string which will be used to write a self deleting python
        # script
        self.python_tmp = ''
        # The jobid returned from the qsub
        self.qsub_id = None
#}}}

# The run_driver
#{{{run_driver
    def run_driver(self, do_run, combination, run_no):
        """The machinery which actually performs the run"""
        if do_run:
            job_name = self.single_submit(combination, run_no)
            # Append the job_name to job_status
            self.run_groups[self.group_no]['job_status'].append(job_name)
        else:
            self.run_groups[self.group_no]['job_status'].append('done')
#}}}

# Functions called directly by the main function
#{{{
#{{{print_run_or_submit
    def print_run_or_submit(self):
        """Prints 'Submitting'"""
        print("\nSubmitting:")
#}}}

#{{{error_checker
    def error_checker(self, **kwargs):
        """Calls all the error checkers"""
        self.qsub_error_check(**kwargs)
#}}}

#{{{single_submit
    def single_submit(self, combination, run_no):
        """Single qsub submission"""
        # Get the script (as a string) which is going to be
        # submitted
        job_name, job_string =\
            self.get_job_string(run_no, combination)

        # The submission
        self.qsub_id = self.submit_to_qsub(job_string)
        return job_name
#}}}

#{{{post_run
    def post_run(self):
        """Creates a self deleting python scripts which calls
        clean_up_runs.

        If we would not submit this a job, it would have caused a bottle
        neck if the driver running the basic_runner class would iterate
        over several folders."""
        # Creates a folder to put the .log and .err files created by the
        # qsub in
        create_folder(self.directory + '/qsub_output')

        # Get the start_time
        start_time = self.get_start_time()

        # The name of the file
        python_name = 'clean_up_'+start_time+'.py'

        # Creating the job string
        job_name = 'clean_up_' + self.run_type + '_'+ start_time

        # Get the core of the job_string (note that we only need to use
        # one node and one processor for this)
        job_string = self.create_qsub_core_string(\
            job_name, '1', '1', self.walltime,\
            folder = self.directory + '/qsub_output/')
        # We will write a python script which calls the
        # relevant bout_plotter

        # First line of the script
        self.python_tmp =\
            'import os\n' +\
            'from bout_runners.common_bout_functions import '+\
            'clean_up_runs\n'
        # Call clean_up_runs
        self.python_tmp +=\
            "clean_up_runs("+\
            str(self.run_groups) + ","+\
            "'" + str(self.directory)  + "')\n"
        # When the script has run, it will delete itself
        self.python_tmp += "os.remove('" + python_name + "')\n"

        # Write the python script
        f = open(python_name, "w")
        f.write(self.python_tmp)
        f.close()

        # Call the python script in the submission
        job_string += 'python ' + python_name + '\n'
        job_string += 'exit'

        # Submit the job
        print('\nSubmitting a script which waits for the runs to finish')
        self.submit_to_qsub(job_string, dependent_job = self.qsub_id)
#}}}
#}}}

# Auxiliary functions
#{{{
#{{{qsub_error_check
    def qsub_error_check(self, **kwargs):
        """Checks for specific qsub errors"""
        variables = [self.nodes, self.ppn, self.walltime, self.mail]
        for variable in variables:
            if variable == False:
                # Check that the non-optional variables are set
                if variable == self.nodes or\
                   variable == self.ppn or\
                   variable == self.walltime:
                    if variable == self.nodes:
                        name = 'self.nodes'
                    elif variable == self.ppn:
                        name = 'self.ppn'
                    elif variable == self.walltime:
                        name = 'self.walltime'
                    self.errors.append("TypeError")
                    raise TypeError (name + " cannot be 'False'.")
            if variable != False:
                # Check that the variables are all given as strings
                if type(variable) != str:
                    self.errors.append("TypeError")
                    raise TypeError ("All non-false data members in"\
                                     " qsub runners must be strings")
                if variable == self.nodes:
                    try:
                        int(variable)
                    except ValueError:
                        self.errors.append("ValueError")
                        raise ValueError ("self.nodes must be given"\
                                          " as a string of an integer")
                elif variable == self.ppn:
                    try:
                        int(variable)
                    except ValueError:
                        self.errors.append("ValueError")
                        raise ValueError ("self.ppn must be given"\
                                          " as a string of an integer")
                elif variable == self.walltime:
                    message = "self.walltime must be on the form 'HH:MM:SS'"
                    # Check if it is given on the form HH:MM:SS
                    walltime_list = self.walltime.split(':')
                    if len(walltime_list) != 3:
                        self.errors.append("ValueError")
                        raise ValueError (message)
                    for walltime_no, walltime_element in enumerate(walltime_list):
                        try:
                            int(walltime_element)
                        except ValueError:
                            self.errors.append("ValueError")
                            raise ValueError (message)
                        # Minutes and seconds can max be 60
                        if walltime_no >= 1 and int(walltime_element) > 60:
                            self.errors.append("ValueError")
                            raise ValueError (message)
                elif variable == self.mail:
                    if ('@' in variable) == False and\
                    ('.' in variable) == False:
                        self.errors.append("ValueError")
                        raise ValueError ("self.mail must be an email"\
                                          "address")
#}}}

#{{{get_job_string
    def get_job_string(self, run_no, combination):
        """Make a string which will act as a shell script when sent to
        qsub."""

        # Find the combination name
        # Split the name to a list
        combination_name = combination.split(' ')
        # Remove whitespaces
        combination_name = [element for element in combination_name\
                            if element != '']
        # Collect the elements
        combination_name = '_'.join(combination_name)
        # Replace bad characters
        combination_name = combination_name.replace(':','')
        combination_name = combination_name.replace('=','-')

        # Name of job
        job_name = combination_name + '_' + self.directory + '_' + str(run_no)

        command = self.get_command_to_run( combination )
        command = 'mpirun -np ' + str(self.nproc) + ' ' + command

        # Print the command
        print(command + '\n')

        # Get the time for start of the submission
        start = datetime.datetime.now()
        start_time = (str(start.year) + '-' + str(start.month) + '-' +\
                      str(start.day) + '.' + str(start.hour) + ":" +\
                      str(start.minute) + ':' + str(start.second))

        # Creating the job string
        job_string = self.create_qsub_core_string(\
            job_name, self.nodes, self.ppn, self.walltime)

        # Start the timer
        job_string += 'start=`date +%s`\n'
        # Run the bout program
        job_string += command + '\n'
        # end the timer
        job_string += 'end=`date +%s`\n'
        # Find the elapsed time
        job_string += 'time=$((end-start))\n'
        # The string is now in seconds
        # The following procedure will convert it to H:M:S
        job_string += 'h=$((time/3600))\n'
        job_string += 'm=$((($time%3600)/60))\n'
        job_string += 's=$((time%60))\n'
        # Ideally we would check if any process were writing to
        # run_log.txt
        # This could be done with lsof command as described in
        # http://askubuntu.com/questions/14252/how-in-a-script-can-i-determine-if-a-file-is-currently-being-written-to-by-ano
        # However, lsof is not available on all clusters
        job_string += "echo '" +\
                      start_time + " "*4 +\
                      self.run_type + " "*4 +\
                      str(run_no) + " "*4 +\
                      self.dmp_folder + " "*4 +\
                      "'$h':'$m':'$s"+\
                      " >> $PBS_O_WORKDIR/" + self.directory +\
                      "/run_log.txt \n"
        # Exit the qsub
        job_string += 'exit'

        return job_name, job_string
#}}}

#{{{get_start_time
    def get_start_time(self):
        """Returns a string of the current time down to micro precision"""
        # The time is going to be appended to the  job name and python name
        time_now = datetime.datetime.now()
        start_time = str(getattr(time_now, 'hour')) + '-' +\
                     str(getattr(time_now,'minute'))+ '-' +\
                     str(getattr(time_now,'second'))
        # In case the process is really fast, so that more than one job
        # is submitted per second, we add a microsecond in the
        # names for safety
        start_time += '-' + str(getattr(time_now,'microsecond'))
        return start_time
#}}}

#{{{create_qsub_core_string
    def create_qsub_core_string(\
        self, job_name, nodes, ppn, walltime, folder=''):
        """Creates the core of a qsub script as a string"""

        # Shebang line
        job_string = '#!/bin/bash\n'
        # The job name
        job_string += '#PBS -N ' + job_name + '\n'
        job_string += '#PBS -l nodes=' + nodes + ':ppn=' + ppn  + '\n'
        # Wall time, must be in format HOURS:MINUTES:SECONDS
        job_string += '#PBS -l walltime=' + walltime + '\n'
        if self.queue != False:
            job_string += '#PBS -q ' + self.queue + '\n'
        job_string += '#PBS -o ' + folder + job_name + '.log' + '\n'
        job_string += '#PBS -e ' + folder + job_name + '.err' + '\n'
        if self.mail != False:
            job_string += '#PBS -M ' + self.mail + '\n'
        # #PBS -m abe
        # a=aborted b=begin e=ended
        job_string += '#PBS -m e ' + '\n'
        # cd to the folder you are sending the qsub from
        job_string += 'cd $PBS_O_WORKDIR ' + '\n'

        return job_string
#}}}

#{{{submit_to_qsub
    def submit_to_qsub(self, job_string, dependent_job=None):
        """Saves the job_string as a shell script, submits it and
        deletes it. Returns the output from qsub as a string"""
        # We will use the subprocess.check_output in order to get the
        # jobid number
        # http://stackoverflow.com/questions/2502833/store-output-of-subprocess-popen-call-in-a-string

        # Create the name of the temporary shell script
        # Get the start_time
        start_time = self.get_start_time()
        script_name = 'tmp_'+start_time+'.sh'

        # Save the string as a script
        with open(script_name, "w") as shell_script:
                shell_script.write(job_string)

        if dependent_job==None:
            output = check_output(["qsub", "./"+script_name])
        else:
            # http://stackoverflow.com/questions/19517923/how-to-wait-for-a-torque-job-array-to-complete
            output = check_output(["qsub", "depend=afterok:"+dependent_job,\
                                    "./" + script_name])
        # Trims the end of the output string
        output = output.strip(' \t\n\r')

        # Delete the shell script
        command = "rm -f "+script_name
        shell(command)

        return output
#}}}
#}}}
#}}}



#{{{qsub_run_with_plots
# Note that the basic_qsub_runner runner is inherited first, since we
# want functions in this class to have precedence over the ones run_with_plots
class qsub_run_with_plots(basic_qsub_runner, run_with_plots):
#{{{docstring
    """Class running BOUT++ in the same way as the basic_qsub_runner, with
    the additional feature that it calls one of the plotters in
    'bout_plotters'.

    For further details, see the documentation of basic_qsub_runner and
    run_with_plots.
    """
#}}}

# The constructor
#{{{__init__
    def __init__(self,\
                 plot_type  = False,\
                 extension  = 'png',\
                 nodes      = '1',\
                 ppn        = '4',\
                 walltime   = '50:00:00',\
                 mail       = False,\
                 queue      = False,\
                 solver     = False,\
                 nproc      = 1,\
                 methods    = False,\
                 n_points   = False,\
                 directory  = 'data',\
                 nout       = False,\
                 timestep   = False,\
                 MXG        = False,\
                 MYG        = False,\
                 additional = False,\
                 restart    = False):
        """Calls the constructors of the super classes."""
        # The cleanest way of doing this is explained in the following link
        # http://stackoverflow.com/questions/13124961/how-to-pass-arguments-efficiently-kwargs-in-python
        # Call the constructors of the super classes
        super(qsub_run_with_plots, self).__init__(plot_type  = plot_type,\
                                                  extension  = extension,\
                                                  nodes      = nodes,\
                                                  ppn        = ppn,\
                                                  walltime   = walltime,\
                                                  mail       = mail,\
                                                  queue      = queue,\
                                                  solver     = solver,\
                                                  nproc      = nproc,\
                                                  methods    = methods,\
                                                  n_points   = n_points,\
                                                  directory  = directory,\
                                                  nout       = nout,\
                                                  timestep   = timestep,\
                                                  MYG        = MYG,\
                                                  MXG        = MXG,\
                                                  additional = additional,\
                                                  restart    = restart)

        self.run_type = 'qsub_plot_' + self.plot_type
##}}}

# Functions called directly by the main function
#{{{
#{{{error_checker
    def error_checker(self, **kwargs):
        """Calls all the error checkers"""

        # Call the error checker for plotter errors from
        # common_bout_functions
        plotter_error_checker =\
           check_for_plotters_errors(self.plot_type, n_points=self.n_points,
                                     timestep=self.timestep, **kwargs)

        # Call the qsub error checker
        self.qsub_error_check()
#}}}

#{{{post_run
# This should not be a post_run at all, but a common for all plotters
    def post_run(self, **kwargs):
        """Submits a job which calls the plotter from bout_plotters"""

        # Make folder to move the error and log files
        create_folder(self.directory + '/qsub_output')

        # Get the start_time
        start_time = self.get_start_time()

        # The name of the file
        python_name = 'tmp'+start_time+'.py'

        # Creating the job string
        job_name = 'post_' + self.run_type + '_'+ start_time

        # The wall-time of the post-processing should be longer than the
        # wall-time of the runs, as the post-processing will wait for
        # the runs to finish
        # Since plotting should not take to long, we add one hour to the
        # wall time of the run
        # Convert the string to a list of strings
        walltime = self.walltime.split(':')
        # Convert them to a string
        walltime = [int(element) for element in walltime]
        # Add an hour to the 'hours'
        walltime[0] += 1
        # Convert walltime back to strings
        walltime = [str(element) for element in walltime]
        # Check that the lenght is two (format needs to be HH:MM:SS)
        for nr in range(len(walltime)):
            if len(walltime[nr]) < 2:
                walltime[nr] = '0' + walltime[nr]
        # Join the list of strings
        walltime = ':'.join(walltime)

        # Get the core of the job_string
        job_string = self.create_qsub_core_string(\
            job_name, nodes='1', ppn='1',\
            walltime=walltime, folder=self.directory + '/qsub_output/')

        # We will write a python script which calls the
        # relevant bout_plotter

        # First line of the script
        self.python_tmp = 'import os\n'

        # Append self.python_tmp with the right plotter
        self.plotter_chooser(**kwargs)

        # When the script has run, it will delete itself
        self.python_tmp += "os.remove('" + python_name + "')\n"
        # Write the python script
        f = open(python_name, "w")
        f.write(self.python_tmp)
        f.close()

        # Call the python script in the submission
        job_string += 'python ' + python_name + '\n'
        job_string += 'exit'

        # Submit the job
        print('\nSubmitting a job which calls ' + self.plot_type)
        self.submit_to_qsub(job_string)
#}}}
#}}}


# Plotter specific
#{{{
#solution_plot specific
#{{{
#{{{solution_plotter
    def solution_plotter(self,\
                         show_plots = False,\
                         collect_x_ghost_points = False,\
                         collect_y_ghost_points = False,\
                         **kwargs):
        """Append self.python_tmp with a creation of the
        solution_plotter instance."""
        # Import the bout_plotters class
        self.python_tmp +=\
            'from bout_runners.bout_plotters import solution_plotter\n'

        # Creates an instance of solution_and_error_plotter
        # Since we set qsub = True, the constructor will call the
        # collect_and_plot function
        # show_plots is set to false when running qsub
        self.python_tmp +=\
          "make_my_plotter=solution_plotter(\n"+\
          "run_groups="             + str(self.run_groups)        +",\n    "+\
          "show_plots="             + str(False)                  +",\n    "+\
          "collect_x_ghost_points=" + str(collect_x_ghost_points) +",\n    "+\
          "collect_y_ghost_points=" + str(collect_y_ghost_points) +",\n    "+\
          "directory='"             + str(self.directory)        +"',\n    "+\
          "file_extension='"        + str(self.file_extension)   +"',\n    "+\
          "variables="              + str(kwargs['variables'])    +",\n    "+\
          "plot_direction="         +\
                                str(kwargs['plot_direction'])     +",\n    "+\
          "plot_times="             + str(kwargs['plot_times'])   +",\n    "+\
          "number_of_overplots="    +\
          "qsub = True"                                          + ")\n"
#}}}
#}}}

#solution_and_error_plotter specific
#{{{
#{{{solution_and_error_plotter
    def solution_and_error_plotter(self,\
                         show_plots = False,\
                         collect_x_ghost_points = False,\
                         collect_y_ghost_points = False,\
                         **kwargs):
        """Append self.python_tmp with a creation of the
        solution_and_error_plotter instance."""

        # Import the bout_plotters class
        self.python_tmp +=\
            'from bout_runners.bout_plotters import solution_and_error_plotter\n'

        # Creates an instance of solution_and_error_plotter
        # Since we set qsub = True, the constructor will call the
        # collect_and_plot function
        # show_plots is set to false when running qsub
        self.python_tmp +=\
          "make_my_plotter=solution_and_error_plotter(\n"+\
          "run_groups="             + str(self.run_groups)        +",\n    "+\
          "show_plots="             + str(False)                  +",\n    "+\
          "collect_x_ghost_points=" + str(collect_x_ghost_points) +",\n    "+\
          "collect_y_ghost_points=" + str(collect_y_ghost_points) +",\n    "+\
          "directory='"             + str(self.directory)        +"',\n    "+\
          "file_extension='"        + str(self.file_extension)   +"',\n    "+\
          "variables="              + str(kwargs['variables'])    +",\n    "+\
          "plot_direction="         +\
                                str(kwargs['plot_direction'])     +",\n    "+\
          "plot_times="             + str(kwargs['plot_times'])   +",\n    "+\
          "number_of_overplots="    +\
                            str(kwargs['number_of_overplots'])    +",\n    "+\
          "qsub = True"                                          + ")\n"
#}}}
#}}}

#convergence_plot specific
#{{{
#{{{convergence_plotter
    def convergence_plotter(self,\
                         show_plots = False,\
                         collect_x_ghost_points = False,\
                         collect_y_ghost_points = False,\
                         **kwargs):
        """Append self.python_tmp with a creation of the convergence_plotter
        instance."""

        # Import the bout_plotters class
        self.python_tmp +=\
            'from bout_runners.bout_plotters import convergence_plotter\n'

        # Creates an instance of solution_and_error_plotter
        # Since we set qsub = True, the constructor will call the
        # collect_and_plot function
        # show_plots is set to false when running qsub
        self.python_tmp +=\
          "make_my_plotter=convergence_plotter(\n"+\
          "run_groups="             + str(self.run_groups)        +",\n    "+\
          "show_plots="             + str(False)                  +",\n    "+\
          "collect_x_ghost_points=" + str(collect_x_ghost_points) +",\n    "+\
          "collect_y_ghost_points=" + str(collect_y_ghost_points) +",\n    "+\
          "directory='"             + str(self.directory)        +"',\n    "+\
          "file_extension='"        + str(self.file_extension)   +"',\n    "+\
          "variables="              + str(kwargs['variables'])    +",\n    "+\
          "convergence_type='"      +\
                                str(kwargs['convergence_type'])  +"',\n    "+\
          "qsub = True"                                          + ")\n"
#}}}
#}}}
#}}}
#}}}



#{{{if __name__ == '__main__':
if __name__ == '__main__':
    """If bout_runners is run as a script, it will just call the demo
    function"""

    print("\n\nTo find out about the bout_runners, please read the user's"+\
          " manual, or have a look at 'BOUT/examples/bout_runners_example'")
#}}}
