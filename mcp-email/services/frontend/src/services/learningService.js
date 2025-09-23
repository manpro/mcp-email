// Smart Learning System with Feedback Loop
class SmartLearningService {
  constructor() {
    this.userActions = JSON.parse(localStorage.getItem('userActions') || '[]')
    this.patterns = JSON.parse(localStorage.getItem('learnedPatterns') || '{}')
    this.confidence = JSON.parse(localStorage.getItem('confidenceScores') || '{}')
    this.vipContacts = new Set(JSON.parse(localStorage.getItem('vipContacts') || '[]'))
    this.responseTimings = JSON.parse(localStorage.getItem('responseTimings') || '{}')
  }

  // Track user action with context
  trackAction(action, email, context = {}) {
    const actionData = {
      action,
      timestamp: Date.now(),
      emailSignature: email ? this.createEmailSignature(email) : null,
      context: {
        timeOfDay: new Date().getHours(),
        dayOfWeek: new Date().getDay(),
        ...context
      }
    }

    this.userActions.push(actionData)

    // Keep only last 1000 actions for performance
    if (this.userActions.length > 1000) {
      this.userActions = this.userActions.slice(-1000)
    }

    this.updatePatterns(actionData)
    this.saveToStorage()

    return this.getRecommendation(email)
  }

  // Create unique signature for email type
  createEmailSignature(email) {
    if (!email) {
      return {
        sender: '',
        domain: '',
        subjectKeywords: [],
        hasAttachments: false,
        isReply: false,
        isForward: false,
        length: 0
      }
    }
    return {
      sender: email.from?.toLowerCase() || '',
      domain: this.extractDomain(email.from),
      subjectKeywords: this.extractKeywords(email.subject),
      hasAttachments: email.attachments?.length > 0,
      isReply: email.subject?.toLowerCase().includes('re:'),
      isForward: email.subject?.toLowerCase().includes('fwd:'),
      length: email.text?.length || 0
    }
  }

  // Extract domain from email address
  extractDomain(email) {
    const match = email?.match(/@([^>]+)/)
    return match ? match[1] : ''
  }

  // Extract keywords from text
  extractKeywords(text) {
    if (!text) return []
    const words = text.toLowerCase().split(/\W+/)
    const stopWords = new Set(['the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were', 'in', 'to', 'for', 'of', 'and', 'or', 'but'])
    return words.filter(w => w.length > 3 && !stopWords.has(w)).slice(0, 5)
  }

  // Update learned patterns
  updatePatterns(actionData) {
    const key = `${actionData.action}_${actionData.emailSignature.domain}`

    if (!this.patterns[key]) {
      this.patterns[key] = {
        count: 0,
        contexts: [],
        lastSeen: null
      }
    }

    this.patterns[key].count++
    this.patterns[key].contexts.push(actionData.context)
    this.patterns[key].lastSeen = actionData.timestamp

    // Update confidence based on repetition
    this.updateConfidence(key, actionData)

    // Track VIP contacts based on response frequency
    if (actionData.action === 'reply' || actionData.action === 'star') {
      this.trackVIPContact(actionData.emailSignature.sender)
    }
  }

  // Update confidence scores
  updateConfidence(patternKey, actionData) {
    if (!this.confidence[patternKey]) {
      this.confidence[patternKey] = 0.1
    }

    // Increase confidence with each occurrence
    const timeSinceLastAction = actionData.timestamp - (this.patterns[patternKey].lastSeen || 0)
    const recencyBoost = timeSinceLastAction < 86400000 ? 0.05 : 0.02 // Less than 24h gets higher boost

    this.confidence[patternKey] = Math.min(0.95, this.confidence[patternKey] + recencyBoost)

    // Decay old patterns
    this.decayOldPatterns()
  }

  // Decay confidence for patterns not seen recently
  decayOldPatterns() {
    const now = Date.now()
    const weekInMs = 7 * 24 * 60 * 60 * 1000

    Object.keys(this.confidence).forEach(key => {
      if (this.patterns[key]?.lastSeen) {
        const age = now - this.patterns[key].lastSeen
        if (age > weekInMs) {
          this.confidence[key] *= 0.95 // 5% decay per week
        }
      }
    })
  }

  // Track VIP contacts
  trackVIPContact(sender) {
    if (!sender) return

    const key = `vip_${sender}`
    if (!this.responseTimings[key]) {
      this.responseTimings[key] = {
        count: 0,
        avgResponseTime: 0,
        lastInteraction: Date.now()
      }
    }

    this.responseTimings[key].count++
    this.responseTimings[key].lastInteraction = Date.now()

    // Mark as VIP if frequently interacted with
    if (this.responseTimings[key].count > 5) {
      this.vipContacts.add(sender)
    }
  }

  // Get AI recommendation for an email
  getRecommendation(email) {
    const signature = this.createEmailSignature(email)
    const recommendations = []

    // Check for learned patterns
    Object.keys(this.patterns).forEach(key => {
      if (key.includes(signature.domain) && this.confidence[key] > 0.6) {
        const [action] = key.split('_')
        recommendations.push({
          action,
          confidence: this.confidence[key],
          reason: `Based on ${this.patterns[key].count} similar actions`
        })
      }
    })

    // Check if VIP contact
    if (this.vipContacts.has(signature.sender)) {
      recommendations.push({
        action: 'star',
        confidence: 0.9,
        reason: 'VIP contact - frequent interaction'
      })
    }

    // Time-based recommendations
    const hour = new Date().getHours()
    if (hour >= 22 || hour <= 6) {
      if (signature.subjectKeywords.some(k => ['urgent', 'emergency', 'critical'].includes(k))) {
        recommendations.push({
          action: 'notify',
          confidence: 0.8,
          reason: 'Urgent email outside work hours'
        })
      }
    }

    // Sort by confidence
    recommendations.sort((a, b) => b.confidence - a.confidence)

    return {
      primaryAction: recommendations[0],
      alternatives: recommendations.slice(1, 3),
      confidence: recommendations[0]?.confidence || 0
    }
  }

  // Get statistics for analytics
  getStatistics() {
    const stats = {
      totalActions: this.userActions.length,
      patternsLearned: Object.keys(this.patterns).length,
      vipContacts: this.vipContacts.size,
      averageConfidence: Object.values(this.confidence).reduce((a, b) => a + b, 0) / Object.keys(this.confidence).length || 0,
      mostCommonActions: this.getMostCommonActions(),
      peakActivityHours: this.getPeakActivityHours()
    }

    return stats
  }

  // Get most common actions
  getMostCommonActions() {
    const actionCounts = {}
    this.userActions.forEach(a => {
      actionCounts[a.action] = (actionCounts[a.action] || 0) + 1
    })

    return Object.entries(actionCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([action, count]) => ({ action, count }))
  }

  // Get peak activity hours
  getPeakActivityHours() {
    const hourCounts = new Array(24).fill(0)
    this.userActions.forEach(a => {
      const hour = new Date(a.timestamp).getHours()
      hourCounts[hour]++
    })

    return hourCounts.map((count, hour) => ({ hour, count }))
  }

  // Predict next action based on current context
  predictNextAction(email, currentTime = new Date()) {
    const predictions = []
    const signature = this.createEmailSignature(email)
    const hour = currentTime.getHours()
    const dayOfWeek = currentTime.getDay()

    // Pattern matching predictions
    this.userActions
      .filter(a => {
        return a.context.timeOfDay === hour &&
               a.emailSignature.domain === signature.domain
      })
      .forEach(a => {
        predictions.push({
          action: a.action,
          confidence: 0.7,
          reason: `Usually ${a.action} at this time`
        })
      })

    // Weekend/weekday patterns
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
    if (isWeekend && signature.subjectKeywords.some(k => ['work', 'project', 'deadline'].includes(k))) {
      predictions.push({
        action: 'snooze',
        confidence: 0.6,
        reason: 'Work email on weekend'
      })
    }

    return predictions
  }

  // Save to localStorage
  saveToStorage() {
    localStorage.setItem('userActions', JSON.stringify(this.userActions))
    localStorage.setItem('learnedPatterns', JSON.stringify(this.patterns))
    localStorage.setItem('confidenceScores', JSON.stringify(this.confidence))
    localStorage.setItem('vipContacts', JSON.stringify([...this.vipContacts]))
    localStorage.setItem('responseTimings', JSON.stringify(this.responseTimings))
  }

  // Clear learning data
  clearLearningData() {
    this.userActions = []
    this.patterns = {}
    this.confidence = {}
    this.vipContacts = new Set()
    this.responseTimings = {}
    this.saveToStorage()
  }
}

// Export singleton instance
export default new SmartLearningService()