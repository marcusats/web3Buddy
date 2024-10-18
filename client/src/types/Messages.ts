type InquiryMessage =  {
    content: string;
    params: { 
      [key: string]: string;
    };
    input?: boolean;
};
 
type Message ={
    content: string;
    role: 'user' | 'assistant';
    timestamp?: string;
    inquiry: boolean; // To track if it's an inquiry message
};

export type {InquiryMessage, Message};


