import {
  Box,
  Button,
  Flex,
  Heading,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useEffect, useMemo, useRef, useState } from "react"
import type { Components } from "react-markdown"
import Markdown from "react-markdown"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import {
  oneLight,
  vscDarkPlus,
} from "react-syntax-highlighter/dist/esm/styles/prism"
import { useWebSocket } from "react-use-websocket/dist/lib/use-websocket"
import remarkGfm from "remark-gfm"
import { OpenAPI } from "@/client"
import { useColorMode, useColorModeValue } from "@/components/ui/color-mode"

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
  const [isAnalysisInProgress, setIsAnalysisInProgress] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Theme-aware colors
  const userMessageBg = useColorModeValue("blue.50", "blue.950")
  const assistantMessageBg = useColorModeValue("bg.subtle", "bg.subtle")
  const mutedTextColor = useColorModeValue("fg.muted", "fg.muted")
  const inlineCodeBg = useColorModeValue("gray.100", "gray.800")
  const inlineCodeColor = useColorModeValue("gray.800", "gray.100")
  const headingColor = useColorModeValue("fg", "fg")
  const linkColor = useColorModeValue("blue.600", "blue.400")
  const blockquoteBg = useColorModeValue("gray.50", "gray.800")
  const tableHeaderBg = useColorModeValue("gray.100", "gray.700")
  const tableRowHoverBg = useColorModeValue("gray.50", "gray.800")
  const { colorMode } = useColorMode()

  // Custom markdown components with Chakra UI styling
  const markdownComponents: Components = useMemo(
    () => ({
      // Headings
      h1: ({ children, ...props }) => (
        <Heading
          as="h1"
          size="xl"
          mb={3}
          mt={4}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      h2: ({ children, ...props }) => (
        <Heading
          as="h2"
          size="lg"
          mb={2}
          mt={3}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      h3: ({ children, ...props }) => (
        <Heading
          as="h3"
          size="md"
          mb={2}
          mt={3}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      h4: ({ children, ...props }) => (
        <Heading
          as="h4"
          size="sm"
          mb={1}
          mt={2}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      h5: ({ children, ...props }) => (
        <Heading
          as="h5"
          size="xs"
          mb={1}
          mt={2}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      h6: ({ children, ...props }) => (
        <Heading
          as="h6"
          size="xs"
          mb={1}
          mt={2}
          color={headingColor}
          {...props}
        >
          {children}
        </Heading>
      ),
      // Paragraphs
      p: ({ children, ...props }) => (
        <Text as="p" mb={3} lineHeight="1.6" color="fg" {...props}>
          {children}
        </Text>
      ),
      // Lists
      ul: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Box
            as="ul"
            pl={6}
            mb={3}
            listStyleType="disc"
            color="fg"
            {...restProps}
          >
            {children}
          </Box>
        )
      },
      ol: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Box
            as="ol"
            pl={6}
            mb={3}
            listStyleType="decimal"
            color="fg"
            {...restProps}
          >
            {children}
          </Box>
        )
      },
      li: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Box as="li" color="fg" mb={1} {...restProps}>
            {children}
          </Box>
        )
      },
      // Links
      a: ({ children, href, ...props }) => {
        // Extract remaining props to avoid ref/node warnings
        const restProps = props as any
        return (
          <Box
            as="a"
            href={href}
            color={linkColor}
            textDecoration="underline"
            _hover={{ textDecoration: "underline", opacity: 0.8 }}
            {...restProps}
          >
            {children}
          </Box>
        )
      },
      // Blockquotes
      blockquote: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Box
            as="blockquote"
            borderLeftWidth="4px"
            borderLeftColor="gray.300"
            pl={4}
            py={2}
            my={3}
            fontStyle="italic"
            color={mutedTextColor}
            bg={blockquoteBg}
            borderRadius="md"
            {...restProps}
          >
            {children}
          </Box>
        )
      },
      // Horizontal rule
      hr: ({ ...props }) => (
        <Box
          as="hr"
          borderTopWidth="1px"
          borderColor="border"
          my={4}
          {...props}
        />
      ),
      // Strong/Bold
      strong: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Text as="strong" fontWeight="bold" color="fg" {...restProps}>
            {children}
          </Text>
        )
      },
      // Emphasis/Italic
      em: ({ children, ...props }) => {
        const restProps = props as any
        return (
          <Text as="em" fontStyle="italic" {...restProps}>
            {children}
          </Text>
        )
      },
      // Code blocks and inline code
      code: (props) => {
        const { children, className, ...rest } = props
        const match = /language-(\w+)/.exec(className || "")
        const language = match ? match[1] : ""
        const codeString = String(children).replace(/\n$/, "")

        // If it's a code block with language, use SyntaxHighlighter
        if (match && language) {
          return (
            <Box my={3}>
              <SyntaxHighlighter
                PreTag="div"
                style={colorMode === "dark" ? vscDarkPlus : oneLight}
                language={language}
                customStyle={{
                  margin: 0,
                  borderRadius: "0.375rem",
                }}
              >
                {codeString}
              </SyntaxHighlighter>
            </Box>
          )
        }

        // Inline code without language
        return (
          <Box
            as="code"
            display="inline"
            px={1}
            py={0.5}
            borderRadius="sm"
            bg={inlineCodeBg}
            color={inlineCodeColor}
            fontSize="0.9em"
            fontFamily="mono"
            className={className}
            {...rest}
          >
            {children}
          </Box>
        )
      },
      // Tables (from remark-gfm)
      table: ({ children, ...props }) => (
        <Box
          as="table"
          width="100%"
          my={3}
          borderCollapse="collapse"
          {...props}
        >
          {children}
        </Box>
      ),
      thead: ({ children, ...props }) => (
        <Box as="thead" bg={tableHeaderBg} {...props}>
          {children}
        </Box>
      ),
      tbody: ({ children, ...props }) => (
        <Box as="tbody" {...props}>
          {children}
        </Box>
      ),
      tr: ({ children, ...props }) => (
        <Box
          as="tr"
          borderBottomWidth="1px"
          borderColor="border"
          _hover={{ bg: tableRowHoverBg }}
          {...props}
        >
          {children}
        </Box>
      ),
      th: ({ children, ...props }) => (
        <Box
          as="th"
          px={3}
          py={2}
          textAlign="left"
          fontWeight="bold"
          borderWidth="1px"
          borderColor="border"
          {...props}
        >
          {children}
        </Box>
      ),
      td: ({ children, ...props }) => (
        <Box
          as="td"
          px={3}
          py={2}
          borderWidth="1px"
          borderColor="border"
          {...props}
        >
          {children}
        </Box>
      ),
    }),
    [
      colorMode,
      inlineCodeBg,
      inlineCodeColor,
      headingColor,
      linkColor,
      mutedTextColor,
      blockquoteBg,
      tableHeaderBg,
      tableRowHoverBg,
    ],
  )

  // Get JWT token from localStorage
  const token = useMemo(() => {
    return localStorage.getItem("access_token") || ""
  }, [])

  // Construct WebSocket URL
  const wsUrl = useMemo(() => {
    if (!token) return null

    // Convert HTTP URL to WS/WSS
    const apiBase =
      OpenAPI.BASE ||
      window.env?.VITE_API_URL ||
      import.meta.env.VITE_API_URL ||
      "http://localhost:8000"
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
          // Stream assessment tokens: Append chunk to last assistant message or create new one
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
          // Keep analysis in progress flag true while receiving assessment chunks
          setIsAnalysisInProgress(true)
          break
        case "response_chunk":
          // Stream response tokens: Append chunk to last assistant message or create new one
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
          // Response chunks don't affect analysis in progress state
          break
        case "assessment_complete":
          // Assessment complete - enable chat input, keep analysis started
          setIsAnalysisInProgress(false)
          setIsAnalysisStarted(true)
          break
        case "response_complete":
          // Response complete - analysis still active, just finished streaming response
          setIsAnalysisInProgress(false)
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
          // Reset analysis progress on error
          setIsAnalysisInProgress(false)
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
      setIsAnalysisInProgress(false)
    }
  }, [lastMessage])

  // Reset conversation when context changes
  useEffect(() => {
    setMessages([])
    setIsAnalysisStarted(false)
    setIsAnalysisInProgress(false)
    setInputValue("")
  }, [])

  // Auto-scroll to latest message when messages change (for streaming)
  useEffect(() => {
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      // Use setTimeout to ensure DOM has updated
      const timeoutId = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 0)
      return () => clearTimeout(timeoutId)
    }
  }, [])

  const handleStartAnalysis = () => {
    if (connectionStatus !== "connected" || !wsUrl || isAnalysisInProgress) {
      console.error("WebSocket not connected or analysis in progress")
      return
    }

    // Mark analysis as in progress immediately
    setIsAnalysisInProgress(true)

    // Send start_analysis message via WebSocket
    sendWebSocketMessage(JSON.stringify({ type: "start_analysis" }))
    // Note: isAnalysisStarted will be set when assessment_complete is received
    // isAnalysisInProgress will be set to false when assessment_complete is received
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
    setIsAnalysisInProgress(false)
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
            disabled={
              connectionStatus !== "connected" || !wsUrl || isAnalysisInProgress
            }
            loading={connectionStatus === "connecting" || isAnalysisInProgress}
          >
            {isAnalysisInProgress
              ? "Analysis in Progress..."
              : "Start Analysis"}
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
              key={`msg-${idx}-${msg.role}`}
              mb={2}
              p={2}
              bg={msg.role === "user" ? userMessageBg : assistantMessageBg}
              borderRadius="md"
            >
              <Box fontWeight="bold" mb={1} color="fg">
                {msg.role === "user" ? "You" : "Assistant"}
              </Box>
              {msg.role === "assistant" ? (
                <Box color="fg" key={`markdown-wrapper-${idx}`}>
                  <Markdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {msg.content}
                  </Markdown>
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
