###############################################################
#  PyNLPl - Evaluation Library
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
# This is a Python library with classes and functions for evaluation
# and experiments .
#
###############################################################    

from pynlpl.statistics import FrequencyList
import subprocess
import itertools
import time
import random
import copy
import datetime
from sys import version_info,stderr

if version_info[0] == 2 and version_info[1] < 6: #python2.5 doesn't have itertools.product
    def itertools_product(*args, **kwds): 
        # product('ABCD', 'xyargdelimiter') --> Ax Ay Bx By Cx Cy Dx Dy
        # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x+[y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)
else:
    itertools_product = itertools.product

class ProcessFailed(Exception):
    pass


class ConfusionMatrix(FrequencyList):
    def __str__(self):
        """Print Confusion Matrix in table form"""
        o = "== Confusion Matrix == (hor: goals, vert: observations)\n\n"

        keys = sorted( set( ( x[1] for x in self._count.keys()) ) )

        linemask = "%20s"
        cells = ['']
        for keyH in keys:
                l = len(keyH)
                if l < 4:
                    l = 4
                elif l > 15:
                    l = 15

                linemask += " %" + str(l) + "s"
                cells.append(keyH)
        linemask += "\n"
        o += linemask % tuple(cells)

        for keyV in keys:
            linemask = "%20s"
            cells = [keyV]
            for keyH in keys:
                l = len(keyH)
                if l < 4:
                    l = 4
                elif l > 15:
                    l = 15
                linemask += " %" + str(l) + "d"
                try:
                    count = self._count[(keyH, keyV)]
                except: 
                    count = 0
                cells.append(count)
            linemask += "\n"
            o += linemask % tuple(cells)
        
        return o



class ClassEvaluation(object):
    def __init__(self,  goals = [], observations = []):
        assert len(observations) == len(goals)
        self.observations = copy.copy(observations)
        self.goals = copy.copy(goals)
 
        self.tp = {}
        self.fp = {}
        self.tn = {}
        self.fn = {}

        self.computed = False
 
        if self.observations:
            self.compute()

    def append(self, goal, observation):
        self.goals.append(goal)
        self.observations.append(observation)
        self.computed = False

    def precision(self, cls=None):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.fp[cls] > 0:
                return self.tp[cls] / float(self.tp[cls] + self.fp[cls])
            else:
                return float('nan')
        else:
            if len(self.observations) > 0:
                return sum( ( self.precision(x) for x in self.observations ) ) / float(len(self.observations))
            else: 
                return float('nan')

    def recall(self, cls=None):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.fn[cls] > 0:
                return self.tp[cls] / float(self.tp[cls] + self.fn[cls])
            else:
                return float('nan')
        else:
            if len(self.observations) > 0:
                return sum( ( self.recall(x) for x in self.observations ) ) / float(len(self.observations))
            else:
                return float('nan')

    def specificity(self, cls=None):
        if not self.computed: self.compute()
        if cls:
            if self.tn[cls] + self.fp[cls] > 0:
                return self.tn[cls] / float(self.tn[cls] + self.fp[cls])
            else:
                return float('nan')
        else:
            if len(self.observations) > 0:
                return sum( ( self.specificity(x) for x in self.observations ) ) / float(len(self.observations))
            else:
                return float('nan')

    def accuracy(self, cls=None):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.tn[cls] + self.fp[cls] + self.fn[cls] > 0:
                return (self.tp[cls]+self.tn[cls]) / float(self.tp[cls] + self.tn[cls] + self.fp[cls] + self.fn[cls])
            else:
                return float('nan')
        else:
            if len(self.observations) > 0:
                return sum( ( self.tp[x] for x in self.tp ) ) / float(len(self.observations))
            else:
                return float('nan')
        
    def fscore(self, cls=None, beta=1):
        if not self.computed: self.compute()
        if cls:
            prec = self.precision(cls)
            rec =  self.recall(cls)
            if prec * rec > 0:
                return (1 + beta*beta) * ((prec * rec) / (beta*beta * prec + rec))
            else:
                return float('nan')
        else:
            if len(self.observations) > 0:
                return sum( ( self.fscore(x) for x in self.observations ) ) / float(len(self.observations))
            else:
                return float('nan')


    def __iter__(self):
        for g,o in zip(self.goals, self.observations):
             yield g,o

    def compute(self):
        self.tp = {}
        self.fp = {}
        self.tn = {}
        self.fn = {}
        for x in set(self.observations + self.goals):
            self.tp[x] = 0
            self.fp[x] = 0
            self.tn[x] = 0
            self.fn[x] = 0

        for goal, observation in self:
            if goal == observation:
                self.tp[observation] += 1
                for goal2, observation2 in zip(self.goals, self.observations):
                    if observation2 != observation and goal2 != goal:
                        self.tn[observation] += 1
                    
                #for g in self.goals:
                #    if g != observation:
                #        self.tn[g] += 1
            elif goal != observation:
                self.fp[observation] += 1
                self.fn[goal] += 1


        l = len(self.goals)
        for o in set(self.observations):
            self.tn[o] = l - self.tp[o] - self.fp[o] - self.fn[o]
            
        self.computed = True


    def confusionmatrix(self, casesensitive =True):
        return ConfusionMatrix(zip(self.goals, self.observations), casesensitive)

    def __str__(self):
        if not self.computed: self.compute()
        o =  "%-15s TP\tFP\tTN\tFN\tAccuracy\tPrecision\tRecall(TPR)\tSpecificity(TNR)\tF-score\n" % ("")
        for cls in set(self.observations):
            o += "%-15s %d\t%d\t%d\t%d\t%4f\t%4f\t%4f\t%4f\t%4f\n" % (cls, self.tp[cls], self.fp[cls], self.tn[cls], self.fn[cls], self.accuracy(cls), self.precision(cls), self.recall(cls),self.specificity(cls),  self.fscore(cls) )
        o += "\nAccuracy             : " + str(self.accuracy()) + "\n"
        o += "Recall      (macroav): "+ str(self.recall()) + "\n"
        o += "Precision   (macroav): " + str(self.precision()) + "\n"
        o += "Specificity (macroav): " + str(self.specificity()) + "\n"
        o += "F-score     (macroav): " + str(self.fscore()) + "\n"
        return o



class AbstractExperiment(object):

    def __init__(self, inputdata = None, **parameters):
        self.inputdata = inputdata
        self.parameters = self.defaultparameters()
        for parameter, value in parameters.items():
            self.parameters[parameter] = value
        self.process = None
        self.creationtime = datetime.datetime.now()
        self.begintime = self.endtime = 0

    def defaultparameters(self):
        return {}

    def duration(self):
        if self.endtime and self.begintime:
            return self.endtime - self.begintime
        else:
            return 0

    def start(self):
        """Start as a detached subprocess, immediately returning execution to caller."""
        raise Exception("Not implemented yet, make sure to overload the start() method in your Experiment class")

    def done(self, warn=True):
        """Is the subprocess done?"""
        if not self.process:
            raise Exception("Not implemented yet or process not started yet, make sure to overload the done() method in your Experiment class")
        self.process.poll()
        if self.process.returncode == None:
            return False
        elif self.process.returncode > 0:
            raise ProcessFailed()
        else:
            self.endtime = datetime.datetime.now()
            return True

    def run(self):
        if hasattr(self,'start'):
            self.start()
            self.wait()
        else:
            raise Exception("Not implemented yet, make sure to overload the run() method!")

    def startcommand(self, command, cwd, stdout, stderr, *arguments, **parameters):
        argdelimiter=' '
        printcommand = True

        cmd = command
        if arguments:
            cmd += ' ' + " ".join([ str(x) for x in arguments])
        if parameters:
            for key, value in parameters.items():
                if key == 'argdelimiter':
                    argdelimiter = value
                elif key == 'printcommand':
                    printcommand = value
                elif isinstance(value, bool) and value == True:
                    cmd += ' ' + key
                elif key[-1] != '=':
                    cmd += ' ' + key + argdelimiter + str(value)
                else:
                    cmd += ' ' + key + str(value)
        if printcommand:
            print "STARTING COMMAND: " + cmd

        self.begintime = datetime.datetime.now()
        if not cwd:
            self.process = subprocess.Popen(cmd, shell=True,stdout=stdout,stderr=stderr)
        else:
            self.process = subprocess.Popen(cmd, shell=True,cwd=cwd,stdout=stdout,stderr=stderr)
        #pid = process.pid
        #os.waitpid(pid, 0) #wait for process to finish
        return self.process

    def wait(self):
        while not self.done():
           time.sleep(1)
           pass

    def score(self):
        raise Exception("Not implemented yet, make sure to overload the score() method")


    def delete(self):
        raise Exception("Not implemented yet, make sure to overload the delete() method")

    def sample(self, size):
        """Return a sample of the input data"""
        raise Exception("Not implemented yet, make sure to overload the sample() method")

class ExperimentPool:
    def __init__(self, size):
        self.size = size
        self.queue = []
        self.running = []

    def append(self, experiment):
        assert isinstance(experiment, AbstractExperiment)
        self.queue.append( experiment )

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def start(self, experiment):
        experiment.start()
        self.running.append( experiment )

    def poll(self, haltonerror=True):
        done = []
        for experiment in self.running:
            try:
                if experiment.done():
                    done.append( experiment )
            except ProcessFailed:
                print >>stderr, "ERROR: One experiment in the pool failed: " + repr(experiment.inputdata) + repr(experiment.parameters)
                if haltonerror:
                    raise
                else:
                    done.append( experiment )
        for experiment in done:
                self.running.remove( experiment )
        return done

    def run(self, haltonerror=True):
        while True:
            #check how many processes are done
            done = self.poll(haltonerror)
                
            for experiment in done:
                yield experiment
            #start new processes
            while self.queue and len(self.running) < self.size:
                self.start( self.queue.pop(0) )
            if not self.queue and not self.running:
                break



class WPSParamSearch(object):
    """ParamSearch with support for Wrapped Progressive Sampling"""
    
    def __init__(self, experimentclass, inputdata, size, parameterscope, poolsize=1, sizefunc=None, prunefunc=None, delete=True): #parameterscope: {'parameter':[values]}
        self.ExperimentClass = experimentclass
        self.inputdata = inputdata
        self.poolsize = poolsize #0 or 1: sequential execution (uses experiment.run() ), >1: parallel execution using ExperimentPool (uses experiment.start() )
        self.maxsize = size
        self.delete = delete #delete intermediate experiments

        if self.maxsize == -1:
            self.sizefunc = lambda x,y: self.maxsize
        else:
            if sizefunc != None:
                self.sizefunc = sizefunc
            else:
                self.sizefunc = lambda i, maxsize: round((maxsize/100.0)*i*i)

        #prunefunc should return a number between 0 and 1, indicating how much is pruned. (for example: 0.75 prunes three/fourth of all combinations, retaining only 25%)
        if prunefunc != None:    
            self.prunefunc = prunefunc
        else:
            self.prunefunc = lambda i: 0.5

        #compute all parameter combinations:
        verboseparameterscope = [ self._combine(x,y) for x,y in parameterscope.items() ]
        self.parametercombinations = [ (x,0) for x in itertools_product(*verboseparameterscope) ] #generator

    def _combine(self,name, values): #TODO: can't we do this inline in a list comprehension?
        l = []
        for value in values:
            l.append( (name, value) )
        return l

    def searchbest(self):
        solution = None
        for s in iter(self):
            solution = s
        return solution[0]


    def test(self):
        #sample size elements from inputdata
        size = int(self.sizefunc(i, self.maxsize))
        if size > self.maxsize:
            return []
    
        if self.maxsize != -1:
            data = self.ExperimentClass.sample(self.inputdata, size)
        else:
            data = self.inputdata        

        #run on ALL available parameter combinations and retrieve score
        newparametercombinations = []
        if self.poolsize <= 1:
            #Don't use experiment pool, sequential execution
            for parameters,score in self.parametercombinations:
                experiment = self.ExperimentClass(data, **dict(parameters))
                experiment.run()
                newparametercombinations.append( (parameters, experiment.score()) )
                if self.delete:
                    experiment.delete()
        else:
            #Use experiment pool, parallel execution
            pool = ExperimentPool(self.poolsize)
            for parameters,score in self.parametercombinations:
                pool.append( self.ExperimentClass(data, **dict(parameters)) )
            for experiment in pool.run(False):
                newparametercombinations.append( (experiment.parameters, experiment.score()) )
                if self.delete:
                    experiment.delete()        
        
        return newparametercombinations


    def __iter__(self):
        i = 0
        while True:
            i += 1

            newparametercombinations = self.test()
            
            #prune the combinations, keeping only the best
            prune = int(round(self.prunefunc(i) * len(newparametercombinations)))
            self.parametercombinations = sorted(newparametercombinations, key=lambda v: v[1])[prune:]

            yield [ x[0] for x in self.parametercombinations ]
            if len(self.parametercombinations) <= 1:
                break

class ParamSearch(WPSParamSearch):
    """A simpler version of ParamSearch without Wrapped Progressive Sampling"""
    def __init__(self, experimentclass, inputdata, parameterscope, poolsize=1, delete=True): #parameterscope: {'parameter':[values]}
        prunefunc = lambda x: 0
        super(ParamSearch, self).__init__(experimentclass, inputdata, -1, parameterscope, poolsize, None,prunefunc, delete)
    
    def __iter__(self):
         for parametercombination, score in sorted(self.test(), key=lambda v: v[1]):
             yield parametercombination, score
                    
        
def filesampler(files, testsetsize = 0.1, devsetsize = 0):
        """Extract a training set, test set and optimally a development set from one file, or multiple *interdependent* files (such as a parallel corpus). It is assumed each line contains one instance (such as a word or sentence for example)."""

        if not isinstance(files, list):
            files = list(files)

        total = 0
        for filename in files:
            f = open(filename,'r')
            count = 0
            for line in f:
                count += 1
            f.close()
            if total == 0:
                total = count
            elif total != count:
                assert Exception("Size mismatch, when multiple files are specified they must contain the exact same amount of lines!")

        #support for relative values:
        if testsetsize < 1:
            testsetsize = int(total * testsetsize)
        if devsetsize < 1 and devsetsize > 0:
            devsetsize = int(total * devsetsize)


        if testsetsize >= total or devsetsize >= total or testsetsize + devsetsize >= total:
            assert Exception("Test set and/or development set too large! No samples left for training set!")


        trainset = {}
        testset = {}
        devset = {}
        for i in range(1,total+1):
            trainset[i] = True
        for i in random.sample(trainset.keys(), testsetsize):
            testset[i] = True
            del trainset[i]
        
        if devsetsize > 0:
            for i in random.sample(trainset.keys(), devsetsize):
                devset[i] = True
                del trainset[i]

        for filename in files:
            ftrain = open(filename + '.train','w')
            ftest = open(filename + '.test','w')
            if devsetsize > 0: fdev = open(filename + '.dev','w')

            f = open(filename,'r')
            for linenum, line in enumerate(f):
                if linenum+1 in trainset:
                    ftrain.write(line)
                elif linenum+1 in testset:
                    ftest.write(line)
                elif devsetsize > 0 and linenum+1 in devset:
                    fdev.write(line)
            f.close()

            ftrain.close()
            ftest.close()
            if devsetsize > 0: fdev.close()




