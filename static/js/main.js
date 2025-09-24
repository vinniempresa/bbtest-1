const stateTranslations = {
    'Federal District': 'Distrito Federal',
    'Sao Paulo': 'São Paulo',
    'Rio de Janeiro': 'Rio de Janeiro',
    'Minas Gerais': 'Minas Gerais',
    'Bahia': 'Bahia',
    'Ceara': 'Ceará',
    'Parana': 'Paraná',
    // Add more state translations as needed
};

async function fetchUserState() {
    try {
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        const rawState = data.region || 'Federal District';
        const state = stateTranslations[rawState] || rawState;
        document.getElementById('state-text').textContent = `Receita Federal - ${state}`;
    } catch (error) {
        console.error('Error fetching user state:', error);
    }
}

function setupPlacaValidation() {
    const placaInput = document.getElementById('placa');
    if (placaInput) {
        placaInput.addEventListener('input', function (e) {
            e.target.value = e.target.value.toUpperCase();
            e.target.value = e.target.value.replace(/[^A-Z0-9]/g, '');
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    fetchUserState();
    setupPlacaValidation();
});