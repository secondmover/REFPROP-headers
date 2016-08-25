import subprocess, sys, six
from numpy.f2py import f2py2e

def generate_interface_file(REFPROP_FORTRAN_path, interface_file_path):
    """
    Use f2py to parse PASS_FTN.FOR to generate a python-directed header file
    """
    # Call f2py programmatically 
    f2py2e.run_main(['--quiet','-h',interface_file_path,REFPROP_FORTRAN_path])
        
def find_subroutine(lines, lineno):
    istart = -1; iend = -1
    for i in range(lineno, len(lines)):
        if 'subroutine' in lines[i]:
            if istart < 0 and iend < 0:
                istart = i
            elif istart >= 0 and iend < 0:
                iend = i
            else:
                break
                
    if istart < 0 and iend < 0:
        return None
    
    # Example: "subroutine pureflddll(icomp) ! in c:\Program Files (x86)\REFPROP\fortran\PASS_FTN.FOR"
    # Example: "subroutine unsetagadll ! in c:\Program Files (x86)\REFPROP\fortran\PASS_FTN.FOR"
    name_part, argument_part = lines[istart].split('(',1)
    sub, name = name_part.rsplit(' ', 1)
    if name == '' and '! in' in sub:
        arguments = []
        name = sub.split('!')[0].split(' ')[1]
    elif '! in' in sub:
        arguments = []
    else:
        arguments = argument_part.split(')')[0].split(',')
    
    argument_list, string_arguments = [], []
    for offset, argument in enumerate(arguments):
        type, argname = lines[istart + 1 + offset].split(' :: ')
        if 'character' in type:
            # Example: "     character*10000 :: hfld"
            string_length = int(type.split('*')[1])
            string_arguments.append((argname.strip()+'_length', string_length))
            argument_list.append((argname.strip(), 'char *'))
        elif 'integer' in type:
            if 'dimension' in type:
                raise ValueError(type)
            argument_list.append((argname.strip(), 'int *'))
        elif 'double' in type:
            L = 0
            if 'dimension' in type:
                L = type.split('dimension(')[1].split(')')[0]
            argument_list.append((argname.strip(), 'double *', L))
        else:
            raise ValueError(lines[istart + 1 + offset].strip())
        
    return dict(istart = istart,
                iend = iend,
                name = name,
                argument_list = argument_list,
                string_arguments = string_arguments
                )
        
def correct_name_case(name):
    return name.upper().replace('DLL','dll')
    
def arguments_to_string(args, string_arguments):
    outs = []
    for arg in args:
        if len(arg) == 2:
            outs.append(arg[1]+arg[0])
        elif len(arg) == 3:
            if arg[2] == 0:
                outs.append(arg[1]+arg[0])
            else:
                outs.append(arg[1]+arg[0]+'/* ' + arg[2] + " */")
        else:
            print arg
    for arg in string_arguments:
        outs.append('int '+arg[0]+'/* ' + str(arg[1]) + " */")
        
    return ', '.join(outs)
        
def generate_function_dict(pyf_file_path):
    """
    Returns JSON data structure for the functions
    """
    istart = 0
    with open(pyf_file_path, 'r') as fp:
        lines = fp.readlines()
        funcs = {}
        output = find_subroutine(lines, istart)
        while output is not None:
            output = find_subroutine(lines, output['iend']+1)
            if output is not None:
                funcname = correct_name_case(output['name'])
                funcs[funcname] = output
    return funcs

header = """
/*
This file was generated by a script in http://github.com/CoolProp/REFPROP-headers
originally written by Ian H. Bell, January 2016

This header should work on windows and linux
*/
"""
def write_header(function_dict, output_header_file):
    """
    Use python to parse the generated interface file
    """
    istart = 0
    ostring = header
    for function in sorted(function_dict.keys()):
        ostring += 'void ' + function + '(' + arguments_to_string(function_dict[function]['argument_list'],function_dict[function]['string_arguments']) + ');\n'

    with open(output_header_file,'w') as fp:
        fp.write(ostring)
    
if __name__=='__main__':
    # Change these paths as needed
    generate_interface_file(r'c:\Program Files (x86)\REFPROP\fortran\PASS_FTN.FOR', 'REFPROP.pyf')
    dd = generate_function_dict('REFPROP.pyf')
    write_header(dd,'REFPROP.h')