import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, ifft
import warnings

warnings.filterwarnings("ignore")

# --- CONSTANTES ---
hbar = 1.054571817e-34
m_electron = 9.1093837015e-31

# --- PARAMÈTRES PHYSIQUES ---
L = 1e-9
N_spatial = 128
dx = L / N_spatial
T_total = 2.0e-15  # Un peu plus long pour voir l'effet
N_temporal = 3000
dt = T_total / N_temporal

x_grid = np.linspace(-L/2, L/2, N_spatial)
k_grid = 2 * np.pi * np.fft.fftfreq(N_spatial, d=dx)

mass = m_electron
sigma_initial = L/40  #De base L/40
OBSERVER_REF = 0.0

# --- HYPOTHÈSE : FORCE PLUS ÉLEVÉE ET POTENTIEL DE FOND RÉDUIT ---
# On réduit la fréquence du potentiel de fond (1e12 au lieu de 1e14)
# Cela rend le puits plus "doux" et laisse l'observateur agir.
FREQ_BASE = 1e12 

# On augmente la gamme de force de l'observateur pour qu'elle domine le potentiel de fond
# De 1e-16 à 1e-10 (beaucoup plus fort)
FORCE_STRENGTHS = [1e-30, 1e-25, 1e-20, 1e-19, 1e-18, 1e-17, 1e-16, 1e-15, 1e-14, 1e-13, 1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e1, 1e10, 1e100] 

print("="*70)
print("TEST AVEC POTENTIEL DE FOND RÉDUIT ET FORCES PLUS ÉLEVÉES")
print("Objectif : Voir l'effet dominant de l'observateur.")
print("="*70)

class CoupledQuantumSystemFFT:
    def __init__(self, L, N_spatial, dt, mass, x0, sigma, observer_ref, force_strength, freq_base):
        self.L = L
        self.N_spatial = N_spatial
        self.dt = dt
        self.mass = mass
        self.dx = L / N_spatial
        self.x = np.linspace(-L/2, L/2, N_spatial)
        self.observer_ref = observer_ref
        self.force_strength = force_strength
        self.freq_base = freq_base
        
        envelope = np.exp(-(self.x - x0)**2 / (2 * sigma**2))
        self.psi = envelope
        self.normalize()
        
        k_squared = k_grid**2
        self.factor_T = np.exp(-1j * (hbar * k_squared / (2 * mass)) * dt)
        
    def normalize(self):
        norm = np.sqrt(np.sum(np.abs(self.psi)**2) * self.dx)
        if norm > 1e-20:
            self.psi /= norm

    def _get_potential(self):
        # Potentiel de fond plus doux
        V_base = 0.5 * self.mass * (self.freq_base**2) * (self.x)**2
        delta = self.x - self.observer_ref
        V_obs = -self.force_strength * np.exp(-(delta**2) / (2 * (L/10)**2))
        return V_base + V_obs

    def evolve_step(self):
        V_pot = self._get_potential()
        self.psi = self.psi * np.exp(-1j * V_pot * (self.dt/2) / hbar)
        psi_k = fft(self.psi)
        psi_k = psi_k * self.factor_T
        self.psi = ifft(psi_k)
        self.psi = self.psi * np.exp(-1j * V_pot * (self.dt/2) / hbar)
        self.normalize()

    def get_observables(self):
        prob = np.abs(self.psi)**2
        x_mean = np.sum(self.x * prob) * self.dx
        
        psi_k = fft(self.psi)
        k_squared = k_grid**2
        T_exp = np.sum(np.abs(psi_k)**2 * (hbar**2 * k_squared / (2 * self.mass))) * self.dx / self.N_spatial
        
        V_exp = np.sum(np.conj(self.psi) * self._get_potential() * self.psi) * self.dx
        E_total = np.real(T_exp + V_exp)
        
        dissonance = abs(x_mean - self.observer_ref)
        return {'x_mean': x_mean, 'E_total': E_total, 'dissonance': dissonance}

    def run_simulation(self, n_steps):
        for _ in range(n_steps):
            self.evolve_step()
        return self.get_observables()

# --- BOUCLE DE TEST ---
results = []

for strength in FORCE_STRENGTHS:
    print(f"\nForce: {strength:.1e} ... ", end="", flush=True)
    
    scores = []
    energies = []
    x_means_final = []
    
    for x0 in [-L/4, -L/8, -L/16]:
        sys = CoupledQuantumSystemFFT(L, N_spatial, dt, mass, x0, sigma_initial, OBSERVER_REF, strength, FREQ_BASE)
        obs_init = sys.get_observables()
        D_init = obs_init['dissonance']
        E_init = obs_init['E_total']
        
        obs_final = sys.run_simulation(N_temporal)
        D_final = obs_final['dissonance']
        E_final = obs_final['E_total']
        x_mean_final = obs_final['x_mean']
        
        reduction = D_init - D_final
        cost = E_final - E_init
        
        scores.append(reduction)
        energies.append(cost)
        x_means_final.append(x_mean_final)
        
    avg_reduction = np.mean(scores)
    avg_cost = np.mean(energies)
    avg_x_mean = np.mean(x_means_final)
    
    results.append({
        'force': strength,
        'reduction': avg_reduction,
        'cost': avg_cost,
        'final_x_mean': avg_x_mean,
        'final_dissonance': avg_x_mean # Approximation car ref=0
    })
    
    # Affichage détaillé
    print(f"Réduction: {avg_reduction*1e9:.3f} nm | Coût: {avg_cost*1e15:.3f} fJ | Pos Finale: {avg_x_mean*1e9:.3f} nm")

# --- AFFICHAGE FINAL DES DONNÉES BRUTES ---
print("\n" + "="*70)
print("TABLEAU DES DONNÉES BRUTES")
print("="*70)
print(f"{'Force (N)':<12} | {'Réduction (nm)':<15} | {'Coût (fJ)':<12} | {'Pos Finale (nm)':<15}")
print("-" * 60)
for r in results:
    print(f"{r['force']:.1e} | {r['reduction']*1e9:.3f} | {r['cost']*1e15:.3f} | {r['final_x_mean']*1e9:.3f}")
print("="*70)

# --- GRAPHIQUE (optionnel, mais utile pour voir la tendance) ---
forces = [r['force'] for r in results]
reductions = [r['reduction'] for r in results]
costs = [r['cost'] for r in results]

plt.figure(figsize=(14, 5))
fig = plt.gcf()
fig.patch.set_facecolor('black')

ax1 = plt.subplot(1, 2, 1)
ax1.plot(forces, reductions, 'o-', color='cyan', markersize=10, linewidth=2)
ax1.set_xscale('log')
ax1.set_xlabel('Force d\'Observation (N)', color='white')
ax1.set_ylabel('Réduction de Dissonance (m)', color='white')
ax1.set_title('Efficacité de l\'Alignement', color='white', fontweight='bold')
ax1.grid(True, which="both", ls="-", alpha=0.3, color='white')
ax1.set_facecolor('black')
for spine in ax1.spines.values(): spine.set_color('white')
ax1.tick_params(colors='white')

ax2 = plt.subplot(1, 2, 2)
ax2.plot(forces, costs, 's-', color='orange', markersize=10, linewidth=2)
ax2.set_xscale('log')
ax2.set_xlabel('Force d\'Observation (N)', color='white')
ax2.set_ylabel('Coût Énergétique (J)', color='white')
ax2.set_title('Coût Énergétique', color='white', fontweight='bold')
ax2.grid(True, which="both", ls="-", alpha=0.3, color='white')
ax2.set_facecolor('black')
for spine in ax2.spines.values(): spine.set_color('white')
ax2.tick_params(colors='white')

plt.tight_layout()
plt.savefig('optimal_coupling_fixed.png', dpi=300, facecolor='black', bbox_inches='tight')
print("\n✅ Graphique sauvegardé : optimal_coupling_fixed.png")
plt.show()

# --- CONCLUSION ---
print("\n" + "="*70)
print("ANALYSE")
print("="*70)
if len(reductions) > 1:
    max_reduction_idx = np.argmax(reductions)
    best_force = forces[max_reduction_idx]
    best_reduction = reductions[max_reduction_idx]
    best_cost = costs[max_reduction_idx]
    
    print(f"🏆 Force Optimale trouvée : {best_force:.1e}")
    print(f"🏆 Meilleure Réduction : {best_reduction*1e9:.3f} nm")
    print(f"🏆 Coût associé : {best_cost*1e15:.3f} fJ")
    
    if best_reduction > 0.2 * 1e-9:
        print("\n✅ VALIDATION DE L'HYPOTHÈSE :")
        print("   Il existe une force d'observation optimale.")
        print("   - Trop faible : Pas d'alignement.")
        print("   - Trop forte : Oscillations (effet de rebond).")
        print("   - Optimale : Alignement maximal avec un coût gérable.")
    else:
        print("\n⚠️  Aucune force n'a permis un alignement significatif.")
else:
    print("Pas assez de données.")
