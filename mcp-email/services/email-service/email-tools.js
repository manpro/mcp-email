/**
 * Email Management Tools - OpenAI Function Calling Format
 * LLM-agnostic tool definitions in JSON Schema format
 * Works with: OpenAI, Anthropic, Ollama, vLLM, LM Studio, etc.
 */

const emailTools = [
  // ============================================
  // EMAIL BASICS (5 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "archive_email",
      description: "Arkivera ett email. Flyttar emailet till arkivet.",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID att arkivera"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "mark_read",
      description: "Markera ett eller flera emails som lästa",
      parameters: {
        type: "object",
        properties: {
          ids: {
            type: "string",
            description: "Kommaseparerade email IDs, t.ex. '123,456,789'"
          }
        },
        required: ["ids"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "search_email",
      description: "Sök efter emails baserat på query",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Sökfras, t.ex. 'maria projekt'"
          },
          limit: {
            type: "string",
            description: "Max antal resultat (default: 20)"
          }
        },
        required: ["query"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_emails",
      description: "Lista emails med filter",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Max antal emails (default: 50)"
          },
          unread: {
            type: "string",
            description: "Endast olästa? 'true' eller 'false'"
          },
          category: {
            type: "string",
            description: "Filtrera på kategori, t.ex. 'inbox', 'work'"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_email",
      description: "Hämta detaljer för ett specifikt email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },

  // ============================================
  // KATEGORIER & REGLER (6 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "create_category",
      description: "Skapa en ny email-kategori",
      parameters: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Internt kategorinamn (lowercase, inga mellanslag)"
          },
          displayName: {
            type: "string",
            description: "Visningsnamn som användaren ser"
          },
          color: {
            type: "string",
            enum: ["blue", "green", "purple", "orange", "red", "pink", "indigo", "cyan"],
            description: "Färg för kategorin"
          }
        },
        required: ["name", "displayName", "color"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_categories",
      description: "Lista alla email-kategorier",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "change_category",
      description: "Byt kategori på ett email",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          },
          category: {
            type: "string",
            description: "Ny kategori, t.ex. 'work', 'personal'"
          }
        },
        required: ["emailId", "category"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "create_rule",
      description: "Skapa en automatisk regel för email-hantering",
      parameters: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Regelns namn"
          },
          condition: {
            type: "string",
            description: "Villkor, t.ex. 'from_domain'"
          },
          value: {
            type: "string",
            description: "Värde för villkoret"
          },
          action: {
            type: "string",
            description: "Åtgärd, t.ex. 'categorize'"
          },
          target: {
            type: "string",
            description: "Mål för åtgärd, t.ex. kategorinamn"
          }
        },
        required: ["name", "condition", "value", "action", "target"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_rules",
      description: "Lista alla automatiska regler",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "delete_rule",
      description: "Ta bort en automatisk regel",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Regel ID"
          }
        },
        required: ["id"]
      }
    }
  },

  // ============================================
  // SNOOZE & BULK (5 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "snooze_email",
      description: "Snooze ett email till senare tidpunkt",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          },
          until: {
            type: "string",
            description: "ISO datetime, t.ex. '2025-10-15T09:00:00'"
          }
        },
        required: ["id", "until"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_snoozed",
      description: "Lista alla snoozade emails",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "bulk_archive",
      description: "Arkivera flera emails samtidigt",
      parameters: {
        type: "object",
        properties: {
          ids: {
            type: "string",
            description: "Kommaseparerade email IDs"
          }
        },
        required: ["ids"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "bulk_delete",
      description: "Radera flera emails samtidigt",
      parameters: {
        type: "object",
        properties: {
          ids: {
            type: "string",
            description: "Kommaseparerade email IDs"
          }
        },
        required: ["ids"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "bulk_snooze",
      description: "Snooze flera emails samtidigt",
      parameters: {
        type: "object",
        properties: {
          ids: {
            type: "string",
            description: "Kommaseparerade email IDs"
          },
          until: {
            type: "string",
            description: "ISO datetime"
          }
        },
        required: ["ids", "until"]
      }
    }
  },

  // ============================================
  // INBOX ZERO & STATS (4 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "get_inbox_stats",
      description: "Hämta Inbox Zero statistik",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_achievements",
      description: "Visa achievements och milstolpar",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "count_emails",
      description: "Räkna antal emails",
      parameters: {
        type: "object",
        properties: {
          type: {
            type: "string",
            description: "Typ att räkna: 'unread', 'total', 'archived'"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "category_stats",
      description: "Statistik per kategori",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },

  // ============================================
  // KONTON & MAPPAR (7 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "list_accounts",
      description: "Lista alla email-konton",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_folders",
      description: "Lista alla mappar",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "move_to_folder",
      description: "Flytta email till mapp",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          },
          folder: {
            type: "string",
            description: "Mappnamn"
          }
        },
        required: ["emailId", "folder"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "sync_account",
      description: "Synka ett email-konto",
      parameters: {
        type: "object",
        properties: {
          accountId: {
            type: "string",
            description: "Konto ID"
          }
        },
        required: ["accountId"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "add_account",
      description: "Lägg till nytt email-konto",
      parameters: {
        type: "object",
        properties: {
          email: {
            type: "string",
            description: "Email-adress"
          },
          provider: {
            type: "string",
            description: "Provider, t.ex. 'gmail', 'outlook'"
          }
        },
        required: ["email", "provider"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "remove_account",
      description: "Ta bort email-konto",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Konto ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "create_folder",
      description: "Skapa ny mapp",
      parameters: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Mappnamn"
          },
          parent: {
            type: "string",
            description: "Parent mapp (optional)"
          }
        },
        required: ["name"]
      }
    }
  },

  // ============================================
  // AI & ML (11 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "analyze_email",
      description: "Analysera email med AI (sentiment, prioritet, osv)",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "suggest_action",
      description: "Föreslå smart action för email",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["emailId"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "summarize_email",
      description: "Sammanfatta email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "extract_contacts",
      description: "Extrahera kontaktinformation från email",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["emailId"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "categorize_batch",
      description: "Kategorisera flera emails med AI",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Antal emails att kategorisera"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "train_ml",
      description: "Träna ML-modell på email-data",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_ml_stats",
      description: "Visa ML statistik och accuracy",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "ml_feedback",
      description: "Ge feedback till ML-modell",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          },
          correctCategory: {
            type: "string",
            description: "Korrekt kategori"
          },
          feedback: {
            type: "string",
            description: "Feedback typ: 'positive' eller 'negative'"
          }
        },
        required: ["emailId", "correctCategory", "feedback"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "ml_status",
      description: "Status på ML kategorisering",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "training_signal",
      description: "Skicka träningssignal till ML",
      parameters: {
        type: "object",
        properties: {
          emailId: {
            type: "string",
            description: "Email ID"
          },
          category: {
            type: "string",
            description: "Kategori"
          },
          confidence: {
            type: "string",
            description: "Konfidens 0-1, t.ex. '0.95'"
          }
        },
        required: ["emailId", "category", "confidence"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "test_rule",
      description: "Testa en regel på ett email",
      parameters: {
        type: "object",
        properties: {
          ruleId: {
            type: "string",
            description: "Regel ID"
          },
          emailId: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["ruleId", "emailId"]
      }
    }
  },

  // ============================================
  // EMAIL OPERATIONS (14 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "delete_email",
      description: "Radera email permanent",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "unsnooze",
      description: "Väck snoozat email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "email_preview",
      description: "Förhandsgranska email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          },
          format: {
            type: "string",
            description: "Format: 'html' eller 'text'"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "mark_unread",
      description: "Markera som oläst",
      parameters: {
        type: "object",
        properties: {
          ids: {
            type: "string",
            description: "Kommaseparerade email IDs"
          }
        },
        required: ["ids"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "flag_email",
      description: "Flagga email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "star_email",
      description: "Stjärnmärk email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "unstar_email",
      description: "Ta bort stjärnmärkning",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "unflag_email",
      description: "Ta bort flagga",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "move_to_inbox",
      description: "Flytta email till inbox",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "unarchive",
      description: "Ta fram arkiverat email",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Email ID"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_recent_emails",
      description: "Hämta senaste emails",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Antal emails (default: 10)"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "update_rule",
      description: "Uppdatera befintlig regel",
      parameters: {
        type: "object",
        properties: {
          id: {
            type: "string",
            description: "Regel ID"
          },
          name: {
            type: "string",
            description: "Nytt namn"
          },
          enabled: {
            type: "string",
            description: "'true' eller 'false'"
          }
        },
        required: ["id"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "batch_process_rules",
      description: "Kör alla regler på emails",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Max emails att processa"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "email_count_verification",
      description: "Verifiera email-antal",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },

  // ============================================
  // MAPPAR (3 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "delete_folder",
      description: "Ta bort mapp",
      parameters: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Mappnamn"
          }
        },
        required: ["name"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "folder_suggestions",
      description: "AI-förslag på mappar",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },

  // ============================================
  // GDPR (4 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "export_data",
      description: "Exportera all data (GDPR)",
      parameters: {
        type: "object",
        properties: {
          format: {
            type: "string",
            description: "Format: 'json' eller 'csv'"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "pending_consent",
      description: "Visa väntande samtycken",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "grant_consent",
      description: "Ge GDPR samtycke",
      parameters: {
        type: "object",
        properties: {
          type: {
            type: "string",
            description: "Samtycketyp, t.ex. 'email_analysis'"
          }
        },
        required: ["type"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "revoke_consent",
      description: "Återkalla samtycke",
      parameters: {
        type: "object",
        properties: {
          type: {
            type: "string",
            description: "Samtycketyp"
          }
        },
        required: ["type"]
      }
    }
  },

  // ============================================
  // PRODUKTIVITET (3 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "weekly_progress",
      description: "Visa veckoframsteg",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "smart_inbox",
      description: "Visa smart inbox (prioriterade emails)",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Antal emails (default: 20)"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_integrations",
      description: "Lista alla integrationer",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },

  // ============================================
  // SYSTEM (4 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "clear_cache",
      description: "Rensa cache",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "cache_stats",
      description: "Visa cache-statistik",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "health_check",
      description: "Systemhälsa",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "undo_action",
      description: "Ångra senaste åtgärd",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "redo_action",
      description: "Gör om ångrad åtgärd",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },

  // ============================================
  // INTEGRATIONER (8 tools)
  // ============================================
  {
    type: "function",
    function: {
      name: "oauth_google",
      description: "Google OAuth integration",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "oauth_microsoft",
      description: "Microsoft OAuth integration",
      parameters: {
        type: "object",
        properties: {},
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "calendar_invites",
      description: "Visa kalenderinbjudningar",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Antal inbjudningar"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "auto_rsvp",
      description: "Auto RSVP på kalenderinbjudan",
      parameters: {
        type: "object",
        properties: {
          eventId: {
            type: "string",
            description: "Event ID"
          },
          response: {
            type: "string",
            description: "'accept', 'decline', eller 'tentative'"
          }
        },
        required: ["eventId", "response"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "browser_automation",
      description: "Starta browser automation",
      parameters: {
        type: "object",
        properties: {
          action: {
            type: "string",
            description: "Action typ, t.ex. 'extract'"
          },
          url: {
            type: "string",
            description: "URL att automata"
          }
        },
        required: ["action", "url"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "automation_history",
      description: "Visa automationshistorik",
      parameters: {
        type: "object",
        properties: {
          limit: {
            type: "string",
            description: "Antal poster"
          }
        },
        required: []
      }
    }
  },
  {
    type: "function",
    function: {
      name: "disconnect_integration",
      description: "Koppla från integration",
      parameters: {
        type: "object",
        properties: {
          type: {
            type: "string",
            description: "Integration typ, t.ex. 'google_calendar'"
          }
        },
        required: ["type"]
      }
    }
  }
];

// Helper function to get tool by name
function getToolByName(name) {
  return emailTools.find(t => t.function.name === name);
}

console.log(`📧 Loaded ${emailTools.length} email management tools`);

// CommonJS export
module.exports = { emailTools, getToolByName };
