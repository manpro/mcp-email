import { useState, useEffect } from 'react'
import EmailManager from './EmailManager'
import MobileEmailView from './MobileEmailView'
import LearningDataViewer from './LearningDataViewer'

// Responsive wrapper that switches between desktop and mobile layouts
export default function ResponsiveEmailManager() {
  const [isMobile, setIsMobile] = useState(false)
  const [isTablet, setIsTablet] = useState(false)
  const [showLearning, setShowLearning] = useState(false)

  useEffect(() => {
    const checkDevice = () => {
      const width = window.innerWidth
      setIsMobile(width < 768)
      setIsTablet(width >= 768 && width < 1024)
    }

    checkDevice()
    window.addEventListener('resize', checkDevice)

    // Show learning data viewer temporarily when mounting
    setShowLearning(true)
    const timer = setTimeout(() => setShowLearning(false), 10000) // Hide after 10 seconds

    return () => {
      window.removeEventListener('resize', checkDevice)
      clearTimeout(timer)
    }
  }, [])

  // Mobile view
  if (isMobile) {
    return (
      <>
        <MobileEmailView />
        {showLearning && <LearningDataViewer />}
      </>
    )
  }

  // Desktop/tablet view - use existing EmailManager with responsive adjustments
  return (
    <>
      <EmailManager isTablet={isTablet} />
      {showLearning && <LearningDataViewer />}
    </>
  )
}