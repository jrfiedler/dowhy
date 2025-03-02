import math

import numpy as np
import pandas as pd
from numpy.random import choice


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def stochastically_convert_to_binary(x):
    p = sigmoid(x)
    return choice([0, 1], 1, p=[1-p, p])


def linear_dataset(beta, num_common_causes, num_samples, num_instruments=0,
                   num_effect_modifiers=0, treatment_is_binary=True):
    W, X, Z, c1, c2, ce, cz = [None]*7
    beta = float(beta)
    if num_common_causes > 0:
        range_c1 = beta*0.5
        range_c2 = beta*0.5
        means = np.random.uniform(-1, 1, num_common_causes)
        cov_mat = np.diag(np.ones(num_common_causes))
        W = np.random.multivariate_normal(means, cov_mat, num_samples)
        c1 = np.random.uniform(0, range_c1, num_common_causes)
        c2 = np.random.uniform(0, range_c2, num_common_causes)

    if num_instruments > 0:
        range_cz = beta*0.5
        p = np.random.uniform(0, 1, num_instruments)
        Z = np.zeros((num_samples, num_instruments))
        for i in range(num_instruments):
            if (i % 2) == 0:
                Z[:, i] = np.random.binomial(n=1, p=p[i], size=num_samples)
            else:
                Z[:, i] = np.random.uniform(0, 1, size=num_samples)
        # Ensure that we do not generate weak instruments
        cz = np.random.uniform(range_cz - (range_cz * 0.25),
                range_cz + (range_cz * 0.25), num_instruments)
    if num_effect_modifiers >0:
        range_ce = beta*0.5
        means = np.random.uniform(-1, 1, num_effect_modifiers)
        cov_mat = np.diag(np.ones(num_effect_modifiers))
        X = np.random.multivariate_normal(means, cov_mat, num_samples)
        ce = np.random.uniform(0, range_ce, num_effect_modifiers)
    # TODO - test all our methods with random noise added to covariates (instead of the stochastic treatment assignment)

    t = np.random.normal(0, 1, num_samples)
    if num_common_causes > 0:
        t += W @ c1  # + np.random.normal(0, 0.01)
    if num_instruments > 0:
        t += Z @ cz
    # Converting treatment to binary if required
    if treatment_is_binary:
        t = np.vectorize(stochastically_convert_to_binary)(t)

    def _compute_y(t, W, X, beta, c2, ce):
        y =  beta*t  # + np.random.normal(0,0.01)
        if num_common_causes > 0:
            y += W @ c2
        if num_effect_modifiers > 0:
            y += (X @ ce) * t
        return y
    y = _compute_y(t, W, X, beta, c2, ce)

    data = np.column_stack((t, y))
    if num_common_causes > 0:
        data = np.column_stack((W, data))
    if num_instruments > 0:
        data = np.column_stack((Z, data))
    if num_effect_modifiers > 0:
        data = np.column_stack((X, data))

    treatment = "v"
    outcome = "y"
    common_causes = [("W" + str(i)) for i in range(0, num_common_causes)]
    ate = np.mean(_compute_y(np.ones(num_samples), W, X, beta, c2, ce) - _compute_y(np.zeros(num_samples), W, X, beta, c2, ce))
    instruments = [("Z" + str(i)) for i in range(0, num_instruments)]
    effect_modifiers =[("X" + str(i)) for i in range(0, num_effect_modifiers)]
    other_variables = None
    col_names = effect_modifiers + instruments + common_causes + [treatment, outcome]
    data = pd.DataFrame(data, columns=col_names)
    # Specifying the correct dtypes
    if treatment_is_binary:
        data = data.astype({treatment:'bool'}, copy=False)

    # Now specifying the corresponding graph strings
    dot_graph = ('digraph {{ {0} ->{1};'
                 ' U[label="Unobserved Confounders"];'
                 ' U->{0}; U->{1};'
                 ).format(treatment, outcome)
    dot_graph = dot_graph + " ".join([v + "-> " + treatment + ";" for v in common_causes])
    dot_graph = dot_graph + " ".join([v + "-> " + outcome + ";" for v in common_causes])
    dot_graph = dot_graph + " ".join([v + "-> " + treatment + ";" for v in instruments])
    dot_graph = dot_graph + " ".join([v + "-> " + outcome + ";" for v in effect_modifiers])
    dot_graph = dot_graph + "}"
    gml_graph = ('graph[directed 1'
                 'node[ id "{0}" label "{0}"]'
                 'node[ id "{1}" label "{1}"]'
                 'node[ id "{2}" label "{2}"]'
                 'edge[source "{0}" target "{1}"]'
                 'edge[source "{2}" target "{0}"]'
                 'edge[source "{2}" target "{1}"]'
                 ).format(treatment, outcome, "Unobserved Confounders")

    gml_graph = gml_graph + " ".join(['node[ id "{0}" label "{0}"] edge[ source "{0}" target "{1}"]'.format(v, treatment) for v in common_causes])
    gml_graph = gml_graph + " ".join(['edge[ source "{0}" target "{1}"]'.format(v, outcome) for v in common_causes])
    gml_graph = gml_graph + " ".join(['node[ id "{0}" label "{0}"] edge[ source "{0}" target "{1}"]'.format(v, treatment) for v in instruments])
    gml_graph = gml_graph + " ".join(['node[ id "{0}" label "{0}"] edge[ source "{0}" target "{1}"]'.format(v, outcome) for v in effect_modifiers])
    gml_graph = gml_graph + ']'
    ret_dict = {
        "df": data,
        "treatment_name": treatment,
        "outcome_name": outcome,
        "common_causes_names": common_causes,
        "instrument_names": instruments,
        "effect_modifier_names": effect_modifiers,
        "dot_graph": dot_graph,
        "gml_graph": gml_graph,
        "ate": ate
    }
    return ret_dict

def xy_dataset(num_samples, effect=True, sd_error=1):
    treatment = 'Treatment'
    outcome = 'Outcome'
    common_causes = ['w0']
    time_var = 's'
    E1 = np.random.normal(loc=0, scale=sd_error, size=num_samples)
    E2 = np.random.normal(loc=0, scale=sd_error, size=num_samples)

    S = np.random.uniform(0, 10, num_samples)
    T1 = 4 - (S - 3) * (S - 3)
    T1[S >= 5] = 0
    T2 = (S - 7) * (S - 7) - 4
    T2[S <= 5] = 0
    W = T1 + T2  # hidden confounder
    if effect:
        U = None
        V = 6 + W + E1
        Y = 6 + V + W + E2  # + (V-8)*(V-8)
    else:
        U = W  # np.random.normal(0, 1, num_samples)
        V = 6 + W + E1
        Y = 12 + W + W + E2  # E2_new
    dat = {
        treatment: V,
        outcome: Y,
        common_causes[0]: W,
        time_var: S
    }
    data = pd.DataFrame(data=dat)
    ret_dict = {
        "df": data,
        "treatment_name": treatment,
        "outcome_name": outcome,
        "common_causes_names": common_causes,
        "time_val": time_var,
        "instrument_names": None,
        "dot_graph": None,
        "gml_graph": None,
        "ate": None,
    }
    return ret_dict
