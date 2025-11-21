import { Box, Button, Flex, Text, Textarea, VStack } from "@chakra-ui/react"
import { useEffect, useMemo, useRef, useState } from "react"
import Markdown from "react-markdown"
import { useWebSocket } from "react-use-websocket/dist/lib/use-websocket"
import remarkGfm from "remark-gfm"
import { OpenAPI } from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"

export type ContextType = "project" | "wbe" | "cost-element" | "baseline"

interface AIChatProps {
  contextType: ContextType
  contextId: string
}

const MAX_MESSAGES = 50 // Maximum number of messages to keep in conversation

export default function AIChat({ contextType, contextId }: AIChatProps) {
  const [messages, setMessages] = useState<
    Array<{ role: "user" | "assistant"; content: string }>
  >([])
  const [inputValue, setInputValue] = useState("")
  const [isAnalysisStarted, setIsAnalysisStarted] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Theme-aware colors
  const userMessageBg = useColorModeValue("blue.50", "blue.950")
  const assistantMessageBg = useColorModeValue("bg.subtle", "bg.subtle")
  const mutedTextColor = useColorModeValue("fg.muted", "fg.muted")

  // Get JWT token from localStorage
  const token = useMemo(() => {
    return localStorage.getItem("access_token") || ""
  }, [])

  // Construct WebSocket URL
  const wsUrl = useMemo(() => {
    if (!token) return null

    // Convert HTTP URL to WS/WSS
    const apiBase =
      OpenAPI.BASE || import.meta.env.VITE_API_URL || "http://localhost:8000"
    const wsBase = apiBase.replace(/^http/, "ws")
    const wsPath = `/api/v1/ai-chat/${contextType}/${contextId}/ws`
    return `${wsBase}${wsPath}?token=${encodeURIComponent(token)}`
  }, [contextType, contextId, token])

  // WebSocket connection - only connect if we have a valid URL and token
  const {
    sendMessage: sendWebSocketMessage,
    lastMessage,
    readyState,
  } = useWebSocket(
    wsUrl ?? null,
    wsUrl
      ? {
          shouldReconnect: () => true, // Auto-reconnect
          reconnectAttempts: 5,
          reconnectInterval: 3000,
          onError: (event) => {
            console.error("WebSocket error:", event)
          },
          onClose: () => {
            console.log("WebSocket connection closed")
          },
          onOpen: () => {
            console.log("WebSocket connection opened")
          },
        }
      : {
          shouldReconnect: () => false,
        },
  )

  // Connection state
  const connectionStatus = useMemo(() => {
    switch (readyState) {
      case 0: // CONNECTING
        return "connecting"
      case 1: // OPEN
        return "connected"
      case 2: // CLOSING
        return "closing"
      case 3: // CLOSED
        return "disconnected"
      default:
        return "disconnected"
    }
  }, [readyState])

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage?.data) return

    try {
      const data = JSON.parse(lastMessage.data)

      switch (data.type) {
        case "assessment_chunk":
        case "response_chunk":
          // Append chunk to last assistant message or create new one
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1]
            if (lastMsg && lastMsg.role === "assistant") {
              // Update existing assistant message by appending chunk
              return [
                ...prev.slice(0, -1),
                { ...lastMsg, content: lastMsg.content + (data.content || "") },
              ]
            }
            // Create new assistant message with chunk
            return [...prev, { role: "assistant", content: data.content || "" }]
          })
          break
        case "assessment_complete":
        case "response_complete":
          // Mark analysis as started when complete
          setIsAnalysisStarted(true)
          break
        case "error":
          // Display error message as assistant message
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Error: ${data.content || "Unknown error"}`,
            },
          ])
          // Don't set isAnalysisStarted on error
          break
        case "status":
          // Status messages can be logged but not displayed
          console.log("Status:", data.content)
          break
        default:
          console.warn("Unknown message type:", data.type)
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error)
    }
  }, [lastMessage])

  // Reset conversation when context changes
  useEffect(() => {
    setMessages([])
    setIsAnalysisStarted(false)
    setInputValue("")
  }, [])

  // Auto-scroll to latest message when messages change
  useEffect(() => {
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [])

  const handleStartAnalysis = () => {
    if (connectionStatus !== "connected" || !wsUrl) {
      console.error("WebSocket not connected")
      return
    }

    // Send start_analysis message via WebSocket
    sendWebSocketMessage(JSON.stringify({ type: "start_analysis" }))
    // Note: isAnalysisStarted will be set when assessment_complete is received
  }

  const handleSendMessage = () => {
    if (!inputValue.trim() || connectionStatus !== "connected" || !wsUrl) {
      return
    }

    const userMessage = inputValue.trim()

    // Add user message to chat immediately
    // Truncate old messages if limit exceeded (keep most recent messages)
    const newUserMessage = { role: "user" as const, content: userMessage }
    const allMessages = [...messages, newUserMessage]
    const updatedMessages =
      allMessages.length > MAX_MESSAGES
        ? allMessages.slice(-MAX_MESSAGES)
        : allMessages
    setMessages(updatedMessages)

    // Clear input field
    setInputValue("")

    // Build conversation history for backend (exclude system messages if any)
    // Conversation history is already limited to MAX_MESSAGES in updatedMessages
    const conversationHistory = updatedMessages
      .filter((msg) => msg.role === "user" || msg.role === "assistant")
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

    // Send message via WebSocket
    sendWebSocketMessage(
      JSON.stringify({
        type: "message",
        content: userMessage,
        conversation_history: conversationHistory,
      }),
    )
  }

  const handleClearConversation = () => {
    setMessages([])
    setIsAnalysisStarted(false)
    setInputValue("")
  }

  return (
    <Box p={4} h="100%">
      <VStack gap={4} align="stretch" h="100%">
        {/* Connection Status Indicator */}
        <Box display="flex" alignItems="center" gap={2}>
          <Box
            w={2}
            h={2}
            borderRadius="full"
            bg={
              connectionStatus === "connected"
                ? "green.500"
                : connectionStatus === "connecting"
                  ? "yellow.500"
                  : "red.500"
            }
            data-testid="connection-status-indicator"
          />
          <Text fontSize="sm" color={mutedTextColor}>
            {connectionStatus === "connected"
              ? "Connected"
              : connectionStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
          </Text>
        </Box>

        {/* Start Analysis Button */}
        {!isAnalysisStarted && (
          <Button
            onClick={handleStartAnalysis}
            colorScheme="blue"
            size="lg"
            disabled={connectionStatus !== "connected" || !wsUrl}
            loading={connectionStatus === "connecting"}
          >
            Start Analysis
          </Button>
        )}

        {/* Message List Container */}
        <Box
          flex="1"
          overflowY="auto"
          p={4}
          borderWidth="1px"
          borderColor="border"
          bg="bg.surface"
          borderRadius="md"
          role="log"
          aria-label="Chat messages"
          data-testid="ai-chat-messages"
        >
          {messages.length === 0 && (
            <Box textAlign="center" color={mutedTextColor} py={8}>
              No messages yet. Start an analysis to begin.
            </Box>
          )}
          {messages.map((msg, idx) => (
            <Box
              key={idx}
              mb={2}
              p={2}
              bg={msg.role === "user" ? userMessageBg : assistantMessageBg}
              borderRadius="md"
            >
              <Box fontWeight="bold" mb={1} color="fg">
                {msg.role === "user" ? "You" : "Assistant"}
              </Box>
              {msg.role === "assistant" ? (
                <Box color="fg">
                  <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                </Box>
              ) : (
                <Box color="fg">{msg.content}</Box>
              )}
            </Box>
          ))}
          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input Area */}
        <Flex gap={2}>
          <Textarea
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSendMessage()
              }
              // Shift+Enter creates a new line (default behavior)
            }}
            disabled={!isAnalysisStarted || connectionStatus !== "connected"}
            resize="none"
            rows={3}
          />
          <VStack>
            <Button
              onClick={handleSendMessage}
              colorScheme="blue"
              disabled={
                !isAnalysisStarted ||
                !inputValue.trim() ||
                connectionStatus !== "connected"
              }
            >
              Send
            </Button>
            <Button
              onClick={handleClearConversation}
              variant="outline"
              size="sm"
              disabled={messages.length === 0 && !isAnalysisStarted}
            >
              Clear Conversation
            </Button>
          </VStack>
        </Flex>
      </VStack>
    </Box>
  )
}
