import Settings from './settings.js';
import Sessions from './sessions.js';
import Chat from './chat.js';
import { playSound } from './sound.js';

// Helper for compact DOM selection
const $ = (id) => document.getElementById(id);

const settings = new Settings();
const sessions = new Sessions();
const chat = new Chat(startStagePolling, stopStagePolling);

document.addEventListener('DOMContentLoaded', async function(){
    // Initialization
    initMode(await settings.getSetting('mode'), await settings.getSessionInfo('stage'));
    initTools(await settings.getSetting('servers'));
    initReporting(await settings.getSessionInfo("report"));
    initStage(await settings.getSessionInfo("stage"));

    // Await init to ensure dropdown is populated before UI binds
    await sessions.init();
    chat.init();
    initPlans();

    sessionListener();

    // Features
    sideBarToggle();
    selectMode();
    selectTools();
    selectStage();
    reportingToggle();
    deleteSession();
    newSession();
    renameSession();
});

function sideBarToggle(){
    const sidebar = $('sidebar');
    const toggleBtn = $('sidebarToggle');
    toggleBtn?.addEventListener('click', () => sidebar?.classList.toggle('collapsed'));
}

function sessionListener(){
    const sessionSelect = $('sessionSelect');
    const selectedSession = $('selectedSession');

    // Load session when selection changes
    sessionSelect?.addEventListener('change', async (e) => {
        const newSession = e.target.value;

        await settings.setSetting('session', newSession);
        if (selectedSession) selectedSession.textContent = newSession;

        await sessions.displaySession(newSession);

        initStage(await settings.getSessionInfo("stage"));
        initReporting(await settings.getSessionInfo("report"));
    });
}

let stagePollingInterval = null;
function startStagePolling(){
    if (stagePollingInterval) return; // Prevent multiple intervals
    // Poll every 10 seconds for stage updates
    stagePollingInterval = setInterval(async () => {
        try {
            const currentStage = await settings.getSessionInfo("stage");
            if (currentStage) initStage(currentStage);
        } catch (error) {
            console.error('Error polling stage:', error);
        }
    }, 10000);
}
function stopStagePolling(){
    if (stagePollingInterval) {
        clearInterval(stagePollingInterval);
        stagePollingInterval = null;
    }
}

// === Mode ===
function selectMode(){
    const modeSelect = $('modeSelect');
    modeSelect?.addEventListener('change', async (e) => {
        const newMode = e.target.value;
        await settings.setSetting('mode', newMode);
        const selectedMode = $('selectedMode');
        if (selectedMode) selectedMode.textContent = newMode;
        initMode(newMode);
    });
}

function initMode(mode, stage){
    mode = mode || 'hawk'; // Fallback
    const hawkPanel = $('hawkPanel');
    const ravenPanel = $('ravenPanel');
    const selectedMode = $('selectedMode');
    const modeSelect = $('modeSelect');
    const userInput = $('userInput');

    if (selectedMode) selectedMode.textContent = mode;
    if (modeSelect) modeSelect.value = mode;

    // Show correct panel
    if (mode === 'raven') {
        ravenPanel?.classList.toggle('hidden', false);
        hawkPanel?.classList.toggle('hidden', true);
        if(stage === 'recon-planning'){
            userInput.placeholder = "Enter IP to initiate pen-testing";
        }else{
            userInput.placeholder = "";
        }
    } else if (mode === 'hawk') {
        hawkPanel?.classList.toggle('hidden', false);
        ravenPanel?.classList.toggle('hidden', true);
        if (userInput) userInput.placeholder = "Hack away!";
    }
}

// === Tools ===
function selectTools(){
    const toolsSelect = $('toolsSelect');
    toolsSelect?.addEventListener('change', async (e) => {
        const newTools = e.target.value;
        await settings.setSetting('servers', newTools);
        const selectedTools = $('selectedTools');
        if (selectedTools) selectedTools.textContent = newTools;
        initTools(newTools);
    });
}

function initTools(tools){
    tools = tools || 'all';
    const selectedTools = $('selectedTools');
    const toolsSelect = $('toolsSelect');
    if (selectedTools) selectedTools.textContent = tools;
    if (toolsSelect) toolsSelect.value = tools;
}

// === Stage ===
function selectStage(){
    const stageSlider = $('stageSlider');
    const stageSignifier = $('stageSignifier');
    const stages = ["recon-planning", "recon", "va-planning", "va", "exploit-planning", "exploit", "finale"];

    stageSlider?.addEventListener('input', async function() {
        const stageName = stages[parseInt(this.value)];
        if (stageSignifier) stageSignifier.textContent = stageName;
        await settings.setSessionInfo('stage', stageName);
    });
}

function initStage(stage){
    const stageSlider = $('stageSlider');
    const stageSignifier = $('stageSignifier');
    const stages = ["recon-planning", "recon", "va-planning", "va", "exploit-planning", "exploit", "finale"];

    stage = stage || stages[0];
    const stageIndex = stages.indexOf(stage);
    const validIndex = stageIndex !== -1 ? stageIndex : 0;

    if (stageSlider) stageSlider.value = validIndex;
    if (stageSignifier) stageSignifier.textContent = stages[validIndex];
}

// === Reporting ===
function reportingToggle(){
    const reportToggle = $('reportToggle');
    const reportSignifier = $('reportSignifier');

    reportToggle?.addEventListener('change', function() {
        const isEnabled = this.checked;
        reportSignifier?.classList.toggle('hidden', !isEnabled);
        settings.setSessionInfo('report', isEnabled);
    });
}

function initReporting(reporting) {
    const reportToggle = $('reportToggle');
    const reportSignifier = $('reportSignifier');

    if (reportToggle) reportToggle.checked = Boolean(reporting);
    reportSignifier?.classList.toggle('hidden', !reporting);
}

// === Session renaming ===
function renameSession(){
    const sessionName = document.getElementById('sessionName');
    const renameSessionInput = document.getElementById('renameSessionInput');
    const sessionSelect = document.getElementById('sessionSelect');
    const renameSession = document.getElementById('renameSession');
    const renameBtns = document.getElementById('renameBtns');
    const confirmRename = document.getElementById('confirmRename');
    const cancelRename = document.getElementById('cancelRename');

    renameSession.addEventListener('click', function(){
        sessionSelect.classList.add('hidden');
        renameSessionInput.classList.remove('hidden');
        renameBtns.classList.remove('hidden');

        renameSessionInput.value = sessionSelect.value.replace('.json', '');
        // playSound("static/audio/hint.wav");
    });
    cancelRename.addEventListener('click', function(){
        renameBtns.classList.add('hidden');
        renameSessionInput.classList.add('hidden');
        sessionSelect.classList.remove('hidden');
        // playSound("static/audio/hint.wav");
    });
    confirmRename.addEventListener('click', async function(){
        // Renaming functionality
        const newName = renameSessionInput.value
        await settings.renamePlanFolder(newName)
        await settings.renameSessionFile(newName)

        await settings.setSetting("session", `${newName}.json`);

        await sessions.init();

        // Visual changes
        renameBtns.classList.add('hidden');
        renameSessionInput.classList.add('hidden');
        sessionSelect.classList.remove('hidden');

        // playSound("static/audio/confirm.wav");
    });
}

// === Session creating ===
function newSession(){
    const newSessionBtn = $('newSessionBtn');
    const newSessionPanel = $('newSessionPanel');
    const newSessionInput = $('newSessionInput');
    const cancelNew = $('cancelNew');
    const confimNew = $('confirmNew');

    newSessionPanel?.classList.add('hidden');

    newSessionBtn?.addEventListener('click', () => {
        newSessionPanel?.classList.remove('hidden');
        newSessionPanel?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        newSessionInput?.focus();
        // playSound("static/audio/hint.wav");

        newSessionInput.value = "";
    });

    cancelNew?.addEventListener('click', () => {
        newSessionPanel?.classList.add('hidden')
        // playSound("static/audio/hint.wav");
    });

    confimNew?.addEventListener('click', async function() {
        const newSessionName = newSessionInput?.value.trim();
        if (!newSessionName) return alert('Please enter a session name');

        try {
            const sessionCreated = await settings.newSession(newSessionName);
            if (sessionCreated) {
                await settings.setSetting("session", `${newSessionName}.json`);
                await sessions.init();
                newSessionPanel?.classList.add('hidden');
                // playSound("static/audio/confirm.wav");
            } else {
                alert('Session already exists or failed to create.');
            }
        } catch (error) {
            console.error('Error creating new session:', error);
            alert('Failed to create new session. Please try again.');
        }
    });
    newSessionInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confimNew?.click();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelNew?.click();
        }
    });
}

// === Session deleting ===
function deleteSession(){
    const deleteSessionBtn = $('deleteSessionBtn');
    const deleteSessionPanel = $('deleteSessionPanel');
    const cancelDelete = $('cancelDelete');
    const confirmDelete = $('confirmDelete');

    deleteSessionPanel?.classList.add('hidden');

    deleteSessionBtn?.addEventListener('click', () => {
        deleteSessionPanel?.classList.remove('hidden');
        deleteSessionPanel?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        deleteSessionPanel?.focus();
        // playSound("static/audio/hint.wav");
    });
    deleteSessionPanel?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmDelete?.click();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelDelete?.click();
        }
    });

    cancelDelete?.addEventListener('click', () => {
        deleteSessionPanel?.classList.add('hidden')
        // playSound("static/audio/hint.wav");
    });

    confirmDelete?.addEventListener('click', async function() {
        const oldSession = await settings.getSetting("session");
        if (!oldSession) return;

        await settings.deleteSession(oldSession);
        await settings.fallbackSession();
        await sessions.init();

        deleteSessionPanel?.classList.add('hidden');
        // playSound("static/audio/confirm.wav");
    });
}

// === Plans ===
function initPlans() {
    const planBtns = document.querySelectorAll('.plan-btn');
    const modal = $('planModal');
    const modalTitle = $('planModalTitle');
    const modalContent = $('planModalContent');
    const closeBtn = $('closePlanModal');

    const planTitles = {
        'summary': 'Summary',
        'recon': 'Reconnaissance Plan',
        'va': 'Vulnerability Assessment Plan',
        'exploit': 'Exploitation Plan'
    };

    planBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const planType = btn.dataset.plan;
            const session = await settings.getSetting('session');

            if (!session || session === 'None') {
                alert('Please select or create a session first.');
                return;
            }

            modalTitle.textContent = planTitles[planType] || 'Plan';
            modalContent.innerHTML = '<p>Loading...</p>';
            modal.classList.remove('hidden');

            try {
                const response = await fetch(`/get-plan?session=${encodeURIComponent(session)}&type=${planType}`);
                const data = await response.json();

                if (response.ok) {
                    // marked.js is already included in index.html
                    modalContent.innerHTML = marked.parse(data.content);
                } else {
                    modalContent.innerHTML = `<p class="error" style="color: #ff6b6b;">Error: ${data.error || 'Failed to load plan'}</p>`;
                }
            } catch (error) {
                console.error('Error loading plan:', error);
                modalContent.innerHTML = '<p class="error" style="color: #ff6b6b;">Failed to load plan. Please try again.</p>';
            }
        });
    });

    closeBtn?.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal?.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
}
