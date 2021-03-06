import os
import re
from subprocess import Popen, PIPE, STDOUT
import SCons

# ----------------------------------------------------------------------
# Protobuf compilation (C++)

def protobuf_scan(node, env, path):
    import_re = re.compile(r'^import\s+"([^"]+)";$', re.M)
    contents = node.get_text_contents()
    imports = import_re.findall(contents)
    #if len(imports):
    #    print node.name, '->', ', '.join(f.path for f in env.File(imports))
    real_imports = []
    # if the expected import doesn't already exist, then it must be generated
    for imp in env.File(imports):
        if not os.path.exists(str(imp)):
            real_imports.append(os.path.join('#', env['BUILD_DIR'], str(imp)))
        else:
            real_imports.append(imp)
    return real_imports

def protobuf_emitter(target, source, env):
    # The emitter must add File (Node) objects so SCons can calculate
    # dependencies properly. Because the File constructor adds the build
    # directory prefix, calculating the correct target path to use means
    # subtracting the target path of the current directory from the path of
    # the existing target.
    gen_base = env.Dir('.').path
    target_hdr = os.path.splitext(target[0].path)[0] + '.h'
    prefix = os.path.commonprefix([gen_base, target_hdr])
    if len(prefix):
        target_hdr = target_hdr[len(prefix + os.sep):]
    target.append(env.File(target_hdr))
    #print source[0].srcnode().path, '->', target[0].path, target[1].path
    return target, source

# The Protobuf generator has special handling for generated proto files
# in order to avoid getting the build directory into the expected import path.
def protobuf_action(target, source, env):
    '''Generate C++ protobuf classes
    '''
    #print str(target[0]), str(source[0])
    wd      = None # use current directory
    out_dir = env['BUILD_DIR']
    src     = str(source[0])
    if str(source[0]).startswith(env['BUILD_DIR']):
        wd      = env['BUILD_DIR']
        out_dir = '.'
        src     = os.path.relpath(src, env['BUILD_DIR'])
    # run the protoc compiler
    cmd = [env['PROTOC'], '-I.', '-I' + env['BUILD_DIR'], '--cpp_out=' + out_dir, src]
    #print cmd, 'cwd=' + os.getcwd(), 'wd=' + wd if wd else 'wd='
    try:
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=wd)
        out, err = proc.communicate()
        rc = proc.returncode
        if rc != 0:
            print ' '.join(cmd)
            print 'error: protoc compiler failed'
            print err
        return rc
    except Exception as ex:
        print ' '.join(cmd)
        print ex
        print '''*** A common cause of this error is that the protoc compiler '{0}'\n    could not be found in the scons PATH.'''.format(env['PROTOC'])
        print 'PATH=' + env['ENV']['PATH']
        return 1

# Protobuf compilation (Python)

# The Python Protobuf generator has special handling for generated proto files
# in order to avoid getting the build directory into the expected import path.
def pyprotobuf_action(target, source, env):
    '''Generate Python protobuf classes
    '''
    #print str(target[0]), str(source[0])
    top_dir = str(env.Dir('#'))
    wd      = None # use current directory
    out_dir = 'python/lib/pyvoyager/proto'  # TODO: use env variable
    src     = str(source[0])
    PROTOCPATH = [top_dir, env['BUILD_DIR']]
    if str(source[0]).startswith(env['BUILD_DIR']):
        wd      = env['BUILD_DIR']
        out_dir = '../../' + out_dir
        src     = os.path.relpath(src, env['BUILD_DIR'])
        PROTOCPATH = [top_dir, '.']
    # run the protoc compiler
    cmd = [env['PROTOC'], '--python_out=' + out_dir, src]
    cmd += ['-I' + d for d in PROTOCPATH]
    try:
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=wd)
        out, err = proc.communicate()
        rc = proc.returncode
        if rc != 0:
            print ' '.join(cmd)
            print 'error: protoc compiler failed'
            print err
        return rc
    except Exception as ex:
        print ' '.join(cmd)
        print ex
        print '''*** A common cause of this error is that the protoc compiler '{0}'\n    could not be found in the scons PATH.'''.format(env['PROTOC'])
        print 'PATH=' + env['ENV']['PATH']
        return 1


def init(env) :
    protobuf_scanner = SCons.Scanner.Scanner(function = protobuf_scan, skeys = ['.proto'])
    env.Append(SCANNERS = protobuf_scanner)

    protobuf_bld = SCons.Builder.Builder(action = SCons.Action.Action(protobuf_action, ' [PROTOC] $SOURCE'),
                           suffix = '.pb.cc',
                           src_suffix = '.proto',
                           emitter = protobuf_emitter)
    env.Append(BUILDERS = {'ProtobufCpp' : protobuf_bld})

    pyprotobuf_bld = SCons.Builder.Builder(action = SCons.Action.Action(pyprotobuf_action, ' [PROTOPY] $SOURCE'),
                             suffix = '_pb2.py',
                             src_suffix = '.proto')
    env.Append(BUILDERS = {'ProtobufPython' : pyprotobuf_bld})
    

