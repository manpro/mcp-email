export default function BriefingsTabSimple() {
  // Debug: Check URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const currentTime = new Date().toLocaleTimeString();
  
  return (
    <div style={{padding: '2rem', minHeight: '400px'}}>
      <div style={{backgroundColor: '#f0f9ff', padding: '1rem', marginBottom: '1rem', borderRadius: '8px', fontSize: '0.875rem'}}>
        <strong>DEBUG INFO ({currentTime}):</strong><br/>
        URL tab param: {urlParams.get('tab')}<br/>
        Current URL: {window.location.href}
      </div>
      <h1 style={{fontSize: '2rem', fontWeight: 'bold', marginBottom: '1rem'}}>
        Daily Briefings
      </h1>
      <p style={{color: '#666', marginBottom: '2rem'}}>
        Important news summarized for morning, lunch and evening
      </p>
      
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem'}}>
        <div style={{backgroundColor: '#fff7ed', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fed7aa'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#c2410c'}}>
            🌅 Morning Briefing
          </h2>
          <p style={{color: '#ea580c', marginBottom: '1rem'}}>
            Overnight and early morning news
          </p>
          <button style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#ea580c',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}>
            Generate Morning Briefing
          </button>
        </div>
        
        <div style={{backgroundColor: '#fefce8', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fde047'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#a16207'}}>
            ☀️ Lunch Briefing
          </h2>
          <p style={{color: '#ca8a04', marginBottom: '1rem'}}>
            Morning developments and updates
          </p>
          <button style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#ca8a04',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}>
            Generate Lunch Briefing
          </button>
        </div>
        
        <div style={{backgroundColor: '#eff6ff', padding: '1.5rem', borderRadius: '8px', border: '1px solid #93c5fd'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#1d4ed8'}}>
            🌙 Evening Briefing
          </h2>
          <p style={{color: '#2563eb', marginBottom: '1rem'}}>
            Daily summary and analysis
          </p>
          <button style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}>
            Generate Evening Briefing
          </button>
        </div>
      </div>
      
      <div style={{marginTop: '2rem', padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '8px'}}>
        <h3 style={{fontWeight: '600', marginBottom: '0.5rem'}}>System Status:</h3>
        <p style={{fontSize: '0.875rem', color: '#666'}}>
          Briefings system is active. Automatic generation scheduled for 08:00, 12:00, and 20:00.
        </p>
      </div>
    </div>
  )
}